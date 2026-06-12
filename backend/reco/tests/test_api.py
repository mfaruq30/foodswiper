"""End-to-end API tests over the in-memory adapters (the same code path the
$0 demo serves with — the Firestore adapter has its own fake-client tests)."""

import random
import uuid

from fastapi.testclient import TestClient

from app.adapters.memory import (
    InMemoryEventLog,
    InMemoryProfileStore,
    InMemoryVenueRepository,
)
from app.auth import AuthError, DevTokenVerifier
from app.main import SERVICE_VERSION, create_app
from app.models import OpenState, Restaurant


# A well-formed swipe body factory — request_id + explore are REQUIRED fields
# (D-008): the deck join key and the exploration label.
def _swipe_body(restaurant_id: str = "v1", direction: str = "right") -> dict[str, object]:
    return {
        "restaurant_id": restaurant_id,
        "mode": "dine_in",
        "direction": direction,
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "card_position": 0,
        "explore": False,
    }


def _venue(rid: str, name: str, cuisine: str, lat: float = 40.7310) -> Restaurant:
    return Restaurant(
        id=rid,
        name=name,
        cuisines=[cuisine],
        price_tier=2,
        price_imputed=True,
        lat=lat,
        lon=-73.9970,
        metro="nyc",
        dietary_tags=[],
        open_state=OpenState.UNKNOWN,
        popularity_prior=0.6,
    )


def _client() -> tuple[TestClient, InMemoryEventLog, InMemoryProfileStore]:
    venues = [
        _venue("v1", "Lucali", "pizza"),
        _venue("v2", "Via Carota", "italian"),
        _venue("v3", "Shake Shack", "burger"),
        _venue("v4", "Sushi Yasuda", "sushi", lat=40.7330),
        _venue("v5", "Joe's Pizza", "pizza"),
    ]
    events = InMemoryEventLog()
    profiles = InMemoryProfileStore()
    app = create_app(
        venues=InMemoryVenueRepository(venues),
        profiles=profiles,
        events=events,
        verifier=DevTokenVerifier(),
        rng=random.Random(7),
    )
    client = TestClient(app)
    client.headers["authorization"] = "Bearer test-user"
    return client, events, profiles


def test_health_is_open_and_versioned() -> None:
    client, _, _ = _client()
    client.headers.pop("authorization")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": SERVICE_VERSION}


def test_v1_requires_auth() -> None:
    client, _, _ = _client()
    client.headers.pop("authorization")
    assert client.get("/v1/profile").status_code == 401
    assert client.post("/v1/deck", json={}).status_code == 401


def test_profile_roundtrip() -> None:
    client, _, _ = _client()
    body = {"home_metro": "nyc", "anchor_cuisines": ["pizza", "italian"], "price_pref": 2}
    assert client.put("/v1/profile", json=body).status_code == 200
    fetched = client.get("/v1/profile").json()
    assert fetched["anchor_cuisines"] == ["pizza", "italian"]
    assert fetched["price_pref"] == 2


def test_deck_serves_cards_and_logs_the_deck() -> None:
    client, events, _ = _client()
    client.put("/v1/profile", json={"home_metro": "nyc", "anchor_cuisines": ["pizza"]})
    response = client.post(
        "/v1/deck", json={"mode": "dine_in", "metro": "nyc", "lat": 40.7308, "lon": -73.9973}
    )
    assert response.status_code == 200
    deck = response.json()
    assert deck["model_version"] == "heuristic-v1"
    assert 1 <= len(deck["cards"]) <= 10
    assert deck["empty_reason"] is None
    # Every card is fully formed: reason text, distance, provenance flags.
    first = deck["cards"][0]
    assert first["reason"]
    assert first["distance_m"] > 0
    # The served deck is logged for training (spec §5) — ids AND the aligned
    # explore flags (the D-008 artifact unbiased eval depends on).
    assert len(events.decks) == 1
    assert events.decks[0].served_ids == [c["restaurant_id"] for c in deck["cards"]]
    assert events.decks[0].explore_flags == [c["explore"] for c in deck["cards"]]


def test_cached_llm_reason_overrides_templated() -> None:
    # D-004: the deck serves templated reasons, but a pre-generated cached
    # reason for (venue, archetype, mode) takes over where present. With no
    # cache (the default _client) every reason stays templated.
    from app.adapters.memory import InMemoryReasonCache
    from app.archetype import archetype_key
    from app.models import UserProfile

    venues = [_venue("v1", "Lucali", "pizza")]
    # The deck user's archetype is what the cache is keyed on.
    archetype = archetype_key(UserProfile(anchor_cuisines=["pizza"]))
    cache = InMemoryReasonCache({("v1", archetype, "dine_in"): "Hand-rolled, your kind of slice"})
    app = create_app(
        venues=InMemoryVenueRepository(venues),
        profiles=InMemoryProfileStore(),
        events=InMemoryEventLog(),
        verifier=DevTokenVerifier(),
        reason_cache=cache,
        rng=random.Random(7),
    )
    client = TestClient(app)
    client.headers["authorization"] = "Bearer test-user"
    client.put("/v1/profile", json={"home_metro": "nyc", "anchor_cuisines": ["pizza"]})
    deck = client.post(
        "/v1/deck", json={"mode": "dine_in", "metro": "nyc", "lat": 40.7308, "lon": -73.9973}
    ).json()
    assert deck["cards"][0]["reason"] == "Hand-rolled, your kind of slice"


def test_deck_respects_dietary_flags_and_signals_empty() -> None:
    # Regression for a real Phase 3 bug: retrieval filters with an empty
    # profile, so the endpoint MUST re-apply the user's hard constraints —
    # a vegan user must never be dealt non-vegan cards. And the empty deck
    # must carry a typed reason so the client can react (D-022).
    client, _, _ = _client()
    client.put("/v1/profile", json={"home_metro": "nyc", "dietary_flags": ["vegan"]})
    response = client.post(
        "/v1/deck", json={"mode": "dine_in", "metro": "nyc", "lat": 40.7308, "lon": -73.9973}
    )
    assert response.status_code == 200
    deck = response.json()
    # None of the fixture venues carry the vegan tag, so the deck is empty —
    # and the reason distinguishes "your filter" from "nothing here".
    assert deck["cards"] == []
    assert deck["empty_reason"] == "no_dietary_matches"


def test_right_swipe_updates_recent_cuisines() -> None:
    client, events, profiles = _client()
    client.put("/v1/profile", json={"home_metro": "nyc", "anchor_cuisines": ["italian"]})
    assert client.post("/v1/swipes", json=_swipe_body("v1", "right")).status_code == 201
    assert len(events.swipes) == 1
    assert events.swipes[0].request_id  # the deck join key is persisted (D-008)
    stored = profiles.get("test-user")
    assert stored is not None
    # v1 is a pizza place — the rolling list now leads with pizza.
    assert stored.recent_right_cuisines[0] == "pizza"


def test_left_swipe_does_not_touch_profile() -> None:
    client, _, profiles = _client()
    client.put("/v1/profile", json={"home_metro": "nyc"})
    client.post("/v1/swipes", json=_swipe_body("v1", "left"))
    stored = profiles.get("test-user")
    assert stored is not None
    assert stored.recent_right_cuisines == []


def test_swipe_validation_rejects_garbage_and_missing_join_keys() -> None:
    client, _, _ = _client()
    bad = {"restaurant_id": "v1", "mode": "dine_in", "direction": "up", "session_id": "nope"}
    assert client.post("/v1/swipes", json=bad).status_code == 422
    # request_id and explore are REQUIRED — omitting them must fail loudly,
    # never default silently (they are the training-label integrity fields).
    incomplete = _swipe_body()
    del incomplete["request_id"]
    assert client.post("/v1/swipes", json=incomplete).status_code == 422
    no_explore = _swipe_body()
    del no_explore["explore"]
    assert client.post("/v1/swipes", json=no_explore).status_code == 422


def test_profile_rejects_out_of_range_cuisine_weights() -> None:
    client, _, _ = _client()
    bad = {"home_metro": "nyc", "cuisine_weights": {"sushi": 1.7}}
    assert client.put("/v1/profile", json=bad).status_code == 422


def test_invalid_token_is_401() -> None:
    class RejectingVerifier:
        def verify(self, token: str) -> str:
            raise AuthError("bad signature")

    app = create_app(
        venues=InMemoryVenueRepository([]),
        profiles=InMemoryProfileStore(),
        events=InMemoryEventLog(),
        verifier=RejectingVerifier(),
    )
    client = TestClient(app)
    response = client.get("/v1/profile", headers={"authorization": "Bearer whatever"})
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid token"


def test_conversion_and_feedback_log() -> None:
    client, events, _ = _client()
    conversion = {"restaurant_id": "v1", "mode": "pickup", "conversion_type": "order_pickup"}
    feedback = {"restaurant_id": "v1", "rating": 1}
    assert client.post("/v1/conversions", json=conversion).status_code == 201
    assert client.post("/v1/feedback", json=feedback).status_code == 201
    assert events.conversions[0].conversion_type == "order_pickup"
    assert events.feedback[0].rating == 1


def test_search_is_prefix_only_like_production() -> None:
    # The memory adapter deliberately mirrors Firestore's prefix-scan
    # capability (the weaker contract): 'luc' finds Lucali; 'pizza' does NOT
    # find "Joe's Pizza" (substring, not prefix).
    client, _, _ = _client()
    results = client.get("/v1/search", params={"metro": "nyc", "q": "luc"}).json()
    assert [r["name"] for r in results] == ["Lucali"]
    substring = client.get("/v1/search", params={"metro": "nyc", "q": "pizza"}).json()
    assert all(r["name"].lower().startswith("pizza") for r in substring)
    assert client.get("/v1/search", params={"metro": "mars", "q": "x"}).status_code == 422


def test_account_deletion_purges_everything_including_auth() -> None:
    deleted_uids: list[str] = []

    class FakeDeleter:
        def delete_user(self, uid: str) -> None:
            deleted_uids.append(uid)

    venues = [_venue("v1", "Lucali", "pizza")]
    events = InMemoryEventLog()
    profiles = InMemoryProfileStore()
    app = create_app(
        venues=InMemoryVenueRepository(venues),
        profiles=profiles,
        events=events,
        verifier=DevTokenVerifier(),
        account_deleter=FakeDeleter(),
    )
    client = TestClient(app)
    client.headers["authorization"] = "Bearer test-user"
    client.put("/v1/profile", json={"home_metro": "nyc"})
    client.post("/v1/swipes", json=_swipe_body())
    response = client.delete("/v1/account")
    assert response.status_code == 200
    assert profiles.get("test-user") is None
    assert events.swipes == []  # D-013: full purge, no orphaned events
    assert deleted_uids == ["test-user"]  # the auth-provider record went too
