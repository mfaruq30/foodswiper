"""Munch API — FastAPI app factory and the /v1 endpoints (spec §6, D-019).

Architecture: the iOS client speaks ONLY this HTTP API — never a database SDK.
That is the portability seam: every handler depends on the ports in app.ports,
wired to Firestore in production (MUNCH_BACKEND=firestore), to the ndjson-
backed in-memory adapter for the $0 demo (MUNCH_BACKEND=memory), and to fakes
in tests via create_app() injection.
"""

from __future__ import annotations

import os
import random
import time
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from .auth import DevTokenVerifier, require_uid
from .deck import assemble_deck
from .filters import hard_filter
from .geo import haversine_m
from .models import Mode, RequestContext, UserProfile
from .ports import (
    AccountDeleter,
    ConversionEvent,
    EventLog,
    FeedbackEvent,
    ProfileStore,
    ServedDeck,
    StoredProfile,
    SwipeEvent,
    TokenVerifier,
    VenueRepository,
)
from .scoring import HeuristicRanker

SERVICE_VERSION = "0.3.0"

# The two launch metros (spec §1). MunchKit's Metro enum mirrors this; the
# seed pipeline's METRO_BOUNDS keys must stay in sync (one constant per
# package — adding a metro is a deliberate cross-package change).
SUPPORTED_METROS = ("nyc", "boston")
_METRO_PATTERN = "^(" + "|".join(SUPPORTED_METROS) + ")$"

# Retrieval defaults; requests above the ceiling are REJECTED (422 via the
# pydantic bound below) — not silently clamped — so the client contract is
# explicit. The cap also keeps a deck request from becoming a metro-wide scan.
DEFAULT_RADIUS_M = 3_000.0
MAX_RADIUS_M = 15_000.0


# --- Request/response schemas (the iOS wire contract) -------------------------


class HealthResponse(BaseModel):
    status: str
    version: str


class ProfileBody(BaseModel):
    display_name: str | None = None
    home_metro: str | None = None
    anchor_cuisines: list[str] = Field(default_factory=list, max_length=20)
    cuisine_weights: dict[str, float] = Field(default_factory=dict)
    price_pref: int | None = Field(default=None, ge=1, le=4)
    dietary_flags: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("cuisine_weights")
    @classmethod
    def _weights_in_unit_interval(cls, weights: dict[str, float]) -> dict[str, float]:
        # The scoring layer documents (and clamps) weights to [0, 1]; reject
        # out-of-range values at the wire so bad data never persists.
        for cuisine, weight in weights.items():
            if not 0.0 <= weight <= 1.0:
                raise ValueError(f"cuisine weight for {cuisine!r} must be in [0, 1]")
        return weights


class DeckRequest(BaseModel):
    mode: Mode
    metro: str = Field(pattern=_METRO_PATTERN)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius_m: float = Field(default=DEFAULT_RADIUS_M, gt=0, le=MAX_RADIUS_M)
    price_ceiling: int | None = Field(default=None, ge=1, le=4)


class CardResponse(BaseModel):
    restaurant_id: str
    name: str
    cuisines: list[str]
    price_tier: int
    price_imputed: bool
    distance_m: float
    # Venue coordinates + optional phone power the client's conversion CTAs
    # (Apple Maps directions, tel:). Coordinates are ODbL open data — safe to
    # expose; attribution ships in-app (spec 8.1).
    lat: float
    lon: float
    phone: str | None
    reason: str
    position: int
    explore: bool


class DeckResponse(BaseModel):
    request_id: str
    model_version: str
    cards: list[CardResponse]
    # Typed empty-deck signal so the client can react ("widen your search?")
    # instead of dead-ending — dietary filters against sparse OSM diet tags
    # can legitimately empty a deck (D-022). None when cards is non-empty.
    empty_reason: str | None = None


class SwipeBody(BaseModel):
    restaurant_id: str
    mode: Mode
    direction: str = Field(pattern="^(left|right)$")
    session_id: uuid.UUID
    # The deck's request_id (echoed from DeckResponse): the training-label
    # join key back to reco_events (D-008). Required — unbackfillable later.
    request_id: uuid.UUID
    card_position: int = Field(ge=0, le=50)
    # Required, no default: a client silently omitting the explore flag would
    # poison the unbiased-eval labels D-008/D-009 exist to protect. The
    # authoritative copy lives in reco_events.explore_flags; this echo is the
    # cross-check.
    explore: bool


class ConversionBody(BaseModel):
    restaurant_id: str
    mode: Mode
    conversion_type: str = Field(pattern="^(directions|call|reserve|order_pickup|order_delivery)$")


class FeedbackBody(BaseModel):
    restaurant_id: str
    rating: int = Field(ge=-1, le=1)


class SearchResult(BaseModel):
    restaurant_id: str
    name: str
    cuisines: list[str]


# Cap on the rolling right-swipe cuisine list that drives swipe_pattern_match;
# beyond ~10 the recency decay (0.85^i) makes older entries negligible anyway.
_RECENT_CUISINES_CAP = 10


def _to_user_profile(stored: StoredProfile | None) -> UserProfile:
    """StoredProfile (persistence shape) -> UserProfile (scoring shape)."""
    if stored is None:
        return UserProfile()
    return UserProfile(
        cuisine_weights=stored.cuisine_weights,
        anchor_cuisines=stored.anchor_cuisines,
        price_pref=stored.price_pref,
        dietary_flags=stored.dietary_flags,
        recent_right_cuisines=stored.recent_right_cuisines,
    )


def create_app(
    venues: VenueRepository,
    profiles: ProfileStore,
    events: EventLog,
    verifier: TokenVerifier,
    account_deleter: AccountDeleter | None = None,
    rng: random.Random | None = None,
) -> FastAPI:
    """Build the API with injected ports — production, demo, and tests all
    come through here; only the adapter set differs. `account_deleter` is
    optional because the memory/demo backend has no auth-provider account to
    remove; production MUST pass one (D-013)."""
    app = FastAPI(title="munch-api", version=SERVICE_VERSION)
    app.state.token_verifier = verifier
    ranker = HeuristicRanker()
    deck_rng = rng or random.Random()

    @app.get("/health")
    def health() -> HealthResponse:
        # Dependency-free on purpose: a failing backend must not mask a live
        # process (Cloud Run probes this).
        return HealthResponse(status="ok", version=SERVICE_VERSION)

    @app.put("/v1/profile")
    def put_profile(body: ProfileBody, uid: str = Depends(require_uid)) -> dict[str, str]:
        existing = profiles.get(uid)
        profiles.upsert(
            StoredProfile(
                uid=uid,
                display_name=body.display_name,
                home_metro=body.home_metro,
                anchor_cuisines=body.anchor_cuisines,
                cuisine_weights=body.cuisine_weights,
                price_pref=body.price_pref,
                dietary_flags=body.dietary_flags,
                # Swipe history is server-maintained; a profile update from
                # onboarding/settings must never wipe it.
                recent_right_cuisines=existing.recent_right_cuisines if existing else [],
            )
        )
        return {"status": "ok"}

    @app.get("/v1/profile")
    def get_profile(uid: str = Depends(require_uid)) -> ProfileBody:
        stored = profiles.get(uid)
        if stored is None:
            raise HTTPException(status_code=404, detail="no profile")
        return ProfileBody(
            display_name=stored.display_name,
            home_metro=stored.home_metro,
            anchor_cuisines=stored.anchor_cuisines,
            cuisine_weights=stored.cuisine_weights,
            price_pref=stored.price_pref,
            dietary_flags=stored.dietary_flags,
        )

    @app.post("/v1/deck")
    def post_deck(body: DeckRequest, uid: str = Depends(require_uid)) -> DeckResponse:
        started = time.monotonic()
        ctx = RequestContext(
            mode=body.mode,
            metro=body.metro,
            user_lat=body.lat,
            user_lon=body.lon,
            max_distance_m=body.radius_m,
            price_ceiling=body.price_ceiling,
        )
        user = _to_user_profile(profiles.get(uid))
        # Retrieval is profile-independent (a range query can't know the user);
        # the user-specific hard constraints — dietary flags, price ceiling —
        # are applied HERE against the real profile, before assembly. Without
        # this line a vegan user would be dealt non-vegan cards.
        candidates = hard_filter(venues.find_candidates(ctx), user, ctx)
        cards = assemble_deck(candidates, user, ctx, deck_rng)

        request_id = str(uuid.uuid4())
        events.record_served_deck(
            ServedDeck(
                request_id=request_id,
                uid=uid,
                mode=body.mode,
                served_ids=[c.restaurant.id for c in cards],
                explore_flags=[c.explore for c in cards],
                model_version=ranker.version,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        )
        empty_reason: str | None = None
        if not cards:
            # Distinguish "your dietary filter emptied this deck" from "there
            # is nothing here" so the client can offer the right next step.
            empty_reason = (
                "no_dietary_matches"
                if user.dietary_flags and venues.find_candidates(ctx)
                else "no_candidates"
            )
        return DeckResponse(
            request_id=request_id,
            model_version=ranker.version,
            empty_reason=empty_reason,
            cards=[
                CardResponse(
                    restaurant_id=c.restaurant.id,
                    name=c.restaurant.name,
                    cuisines=c.restaurant.cuisines,
                    price_tier=c.restaurant.price_tier,
                    price_imputed=c.restaurant.price_imputed,
                    distance_m=round(
                        haversine_m(body.lat, body.lon, c.restaurant.lat, c.restaurant.lon), 1
                    ),
                    lat=c.restaurant.lat,
                    lon=c.restaurant.lon,
                    phone=c.restaurant.phone,
                    reason=c.reason,
                    position=c.position,
                    explore=c.explore,
                )
                for c in cards
            ],
        )

    @app.post("/v1/swipes", status_code=201)
    def post_swipe(body: SwipeBody, uid: str = Depends(require_uid)) -> dict[str, str]:
        events.record_swipe(
            SwipeEvent(
                uid=uid,
                restaurant_id=body.restaurant_id,
                mode=body.mode,
                direction=body.direction,
                session_id=str(body.session_id),
                request_id=str(body.request_id),
                card_position=body.card_position,
                explore=body.explore,
            )
        )
        if body.direction == "right":
            # Maintain the rolling recent-cuisines list that feeds
            # swipe_pattern_match — most recent first, capped.
            stored = profiles.get(uid)
            matched = venues.get_by_ids([body.restaurant_id])
            if stored is not None and matched and matched[0].cuisines:
                stored.recent_right_cuisines = (
                    [matched[0].cuisines[0], *stored.recent_right_cuisines]
                )[:_RECENT_CUISINES_CAP]
                profiles.upsert(stored)
        return {"status": "ok"}

    @app.post("/v1/conversions", status_code=201)
    def post_conversion(body: ConversionBody, uid: str = Depends(require_uid)) -> dict[str, str]:
        events.record_conversion(
            ConversionEvent(
                uid=uid,
                restaurant_id=body.restaurant_id,
                mode=body.mode,
                conversion_type=body.conversion_type,
            )
        )
        return {"status": "ok"}

    @app.post("/v1/feedback", status_code=201)
    def post_feedback(body: FeedbackBody, uid: str = Depends(require_uid)) -> dict[str, str]:
        events.record_feedback(
            FeedbackEvent(uid=uid, restaurant_id=body.restaurant_id, rating=body.rating)
        )
        return {"status": "ok"}

    @app.get("/v1/search")
    def search(
        metro: str, q: str, limit: int = 10, uid: str = Depends(require_uid)
    ) -> list[SearchResult]:
        # Onboarding anchor autocomplete — against Munch's own inventory only
        # (spec §6.2: no external API, no key).
        if metro not in SUPPORTED_METROS:
            raise HTTPException(status_code=422, detail="unknown metro")
        results = venues.search_by_name(metro, q, min(max(limit, 1), 25))
        return [SearchResult(restaurant_id=r.id, name=r.name, cuisines=r.cuisines) for r in results]

    @app.delete("/v1/account")
    def delete_account(uid: str = Depends(require_uid)) -> dict[str, str]:
        # Full purge (D-013): events first, then profile, then the auth
        # provider's account record. FUTURE(Phase 6): Apple SIWA token
        # revocation (TN3194) goes here, BEFORE the auth-account deletion.
        events.delete_user_events(uid)
        profiles.delete(uid)
        if account_deleter is not None:
            account_deleter.delete_user(uid)
        return {"status": "deleted"}

    return app


def _build_production_app() -> FastAPI:
    """Wire adapters from environment — the uvicorn entry point.

    MUNCH_BACKEND=memory  -> ndjson venues, in-memory events (the $0 demo)
    MUNCH_BACKEND=firestore -> project food-5eb2a via Admin SDK (default)
    MUNCH_AUTH=dev        -> token==uid (demo only; default is Firebase)

    All Firebase/Firestore construction lives in adapters.firestore — this
    function never imports google.cloud or firebase_admin (D-019 seam).
    """
    backend = os.environ.get("MUNCH_BACKEND", "firestore")
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "food-5eb2a")

    verifier: TokenVerifier
    account_deleter: AccountDeleter | None = None
    if os.environ.get("MUNCH_AUTH", "firebase") == "dev":
        verifier = DevTokenVerifier()
    else:
        from .adapters.firestore import FirebaseTokenVerifier

        firebase_verifier = FirebaseTokenVerifier(project_id)
        verifier = firebase_verifier
        account_deleter = firebase_verifier

    if backend == "memory":
        from .adapters.memory import (
            InMemoryEventLog,
            InMemoryProfileStore,
            InMemoryVenueRepository,
        )

        ndjson = Path(os.environ.get("VENUES_NDJSON", "venues.ndjson"))
        return create_app(
            venues=InMemoryVenueRepository.from_ndjson(ndjson),
            profiles=InMemoryProfileStore(),
            events=InMemoryEventLog(),
            verifier=verifier,
            account_deleter=account_deleter,
        )

    from .adapters.firestore import build_firestore_backend

    venues, profiles, events = build_firestore_backend(project_id)
    return create_app(
        venues=venues,
        profiles=profiles,
        events=events,
        verifier=verifier,
        account_deleter=account_deleter,
    )


# uvicorn app.main:app — built lazily so importing this module for tests never
# constructs production adapters.
def __getattr__(name: str) -> FastAPI:
    if name == "app":
        return _build_production_app()
    raise AttributeError(name)
