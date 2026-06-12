"""Ports: the seams between the reco core and the outside world.

THE portability contract (promised in D-019's "switch back later" path):
everything above these protocols — scoring, deck assembly, the HTTP API — is
backend-agnostic. Swapping Firestore for Postgres later means writing new
implementations of these protocols (adapters/), not touching anything else.
Tests inject in-memory fakes through the same seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .models import Mode, RequestContext, Restaurant


@dataclass(slots=True)
class StoredProfile:
    """A user's persisted taste profile as the data layer returns it."""

    uid: str
    display_name: str | None = None
    home_metro: str | None = None
    anchor_cuisines: list[str] = field(default_factory=list)
    cuisine_weights: dict[str, float] = field(default_factory=dict)
    price_pref: int | None = None
    dietary_flags: list[str] = field(default_factory=list)
    recent_right_cuisines: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SwipeEvent:
    """One swipe, exactly as logged (D-008: position + explore are mandatory).

    `request_id` joins the swipe back to its served deck (reco_events row) —
    THE training-label join key. Without it, deck attribution degrades to
    uid+venue+timestamp heuristics that break whenever a venue is re-served;
    and it cannot be backfilled after launch.
    """

    uid: str
    restaurant_id: str
    mode: Mode
    direction: str  # 'left' | 'right'
    session_id: str
    request_id: str
    card_position: int
    explore: bool


@dataclass(slots=True)
class ConversionEvent:
    """An outbound tap — logged honestly as a tap, not a confirmed order (D-010)."""

    uid: str
    restaurant_id: str
    mode: Mode
    conversion_type: str  # 'directions' | 'call' | 'reserve' | 'order_pickup' | 'order_delivery'


@dataclass(slots=True)
class FeedbackEvent:
    """Post-visit thumbs: -1 / 0 / 1."""

    uid: str
    restaurant_id: str
    rating: int


@dataclass(slots=True)
class ServedDeck:
    """The training/eval log row for one served deck (spec §5 reco_events)."""

    request_id: str
    uid: str
    mode: Mode
    served_ids: list[str]
    explore_flags: list[bool]
    model_version: str
    latency_ms: int


class VenueRepository(Protocol):
    """Candidate retrieval — the geospatial seam.

    The Firestore adapter answers `find_candidates` with geohash range queries
    + precise haversine post-filtering; a future Postgres adapter answers it
    with one ST_DWithin query. Same contract, different engine (D-019).
    """

    def find_candidates(self, ctx: RequestContext) -> list[Restaurant]: ...

    def get_by_ids(self, ids: list[str]) -> list[Restaurant]: ...

    def search_by_name(self, metro: str, query: str, limit: int) -> list[Restaurant]: ...


class ProfileStore(Protocol):
    """User taste profiles, keyed by auth uid."""

    def get(self, uid: str) -> StoredProfile | None: ...

    def upsert(self, profile: StoredProfile) -> None: ...

    def delete(self, uid: str) -> None: ...


class EventLog(Protocol):
    """Append-only behavioral events — the Layer-4 training data."""

    def record_swipe(self, event: SwipeEvent) -> None: ...

    def record_conversion(self, event: ConversionEvent) -> None: ...

    def record_feedback(self, event: FeedbackEvent) -> None: ...

    def record_served_deck(self, deck: ServedDeck) -> None: ...

    def delete_user_events(self, uid: str) -> None: ...


class ReasonCache(Protocol):
    """Pre-generated LLM reason text, keyed by (restaurant_id, archetype, mode).

    The LLM is OFF the serve path (D-004): the deck serves templated reasons
    instantly, and this batch read swaps in a cached LLM reason ONLY where one
    already exists. Empty cache (the $0 demo) => every card keeps its templated
    reason, no LLM call, no key. A background job populates it.
    """

    def get_many(self, keys: list[tuple[str, str, str]]) -> dict[tuple[str, str, str], str]: ...


class TokenVerifier(Protocol):
    """Auth seam: bearer token -> verified uid (raises on invalid).

    Firebase ID tokens now; a Supabase JWT verifier later. Contained in a port
    so the untyped firebase_admin surface never leaks into the API layer.
    """

    def verify(self, token: str) -> str: ...


class AccountDeleter(Protocol):
    """Deletes the AUTH PROVIDER's account record (part of the D-013 purge).

    Declared explicitly — not duck-typed off the verifier — because account
    deletion is a compliance contract (Apple 5.1.1(v)), and in Phase 6 the
    implementation must also revoke the Apple SIWA token (TN3194) before
    removing the Firebase user.
    """

    def delete_user(self, uid: str) -> None: ...
