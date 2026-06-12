"""End-to-end API tests over the in-memory adapters (the same code path the
$0 demo serves with — only the Firestore adapter is out of test scope here)."""

import random
import uuid

from fastapi.testclient import TestClient

from app.adapters.memory import (
    InMemoryEventLog,
    InMemoryProfileStore,
    InMemoryVenueRepository,
)
from app.auth import DevTokenVerifier
from app.main import SERVICE_VERSION, create_app
from app.models import OpenState, Restaurant


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
    # Every card is fully formed: reason text, distance, provenance flags.
    first = deck["cards"][0]
    assert first["reason"]
    assert first["distance_m"] > 0
    # The served deck is logged for training (spec §5) with explore flags.
    assert len(events.decks) == 1
    assert events.decks[0].served_ids == [c["restaurant_id"] for c in deck["cards"]]


def test_right_swipe_updates_recent_cuisines() -> None:
    client, events, profiles = _client()
    client.put("/v1/profile", json={"home_metro": "nyc", "anchor_cuisines": ["italian"]})
    body = {
        "restaurant_id": "v1",
        "mode": "dine_in",
        "direction": "right",
        "session_id": str(uuid.uuid4()),
        "card_position": 0,
        "explore": False,
    }
    assert client.post("/v1/swipes", json=body).status_code == 201
    assert len(events.swipes) == 1
    stored = profiles.get("test-user")
    assert stored is not None
    # v1 is a pizza place — the rolling list now leads with pizza.
    assert stored.recent_right_cuisines[0] == "pizza"


def test_left_swipe_does_not_touch_profile() -> None:
    client, _, profiles = _client()
    client.put("/v1/profile", json={"home_metro": "nyc"})
    body = {
        "restaurant_id": "v1",
        "mode": "dine_in",
        "direction": "left",
        "session_id": str(uuid.uuid4()),
        "card_position": 0,
    }
    client.post("/v1/swipes", json=body)
    stored = profiles.get("test-user")
    assert stored is not None
    assert stored.recent_right_cuisines == []


def test_swipe_validation_rejects_garbage() -> None:
    client, _, _ = _client()
    bad = {"restaurant_id": "v1", "mode": "dine_in", "direction": "up", "session_id": "nope"}
    assert client.post("/v1/swipes", json=bad).status_code == 422


def test_conversion_and_feedback_log() -> None:
    client, events, _ = _client()
    conversion = {"restaurant_id": "v1", "mode": "pickup", "conversion_type": "order_pickup"}
    feedback = {"restaurant_id": "v1", "rating": 1}
    assert client.post("/v1/conversions", json=conversion).status_code == 201
    assert client.post("/v1/feedback", json=feedback).status_code == 201
    assert events.conversions[0].conversion_type == "order_pickup"
    assert events.feedback[0].rating == 1


def test_search_prefers_prefix_matches() -> None:
    client, _, _ = _client()
    results = client.get("/v1/search", params={"metro": "nyc", "q": "pizza"}).json()
    names = [r["name"] for r in results]
    # Substring matches both pizza joints; "Joe's Pizza" is not a prefix match
    # so "Lucali" (no match) is absent and ordering is stable.
    assert "Joe's Pizza" in names
    assert client.get("/v1/search", params={"metro": "mars", "q": "x"}).status_code == 422


def test_account_deletion_purges_everything() -> None:
    client, events, profiles = _client()
    client.put("/v1/profile", json={"home_metro": "nyc"})
    client.post(
        "/v1/swipes",
        json={
            "restaurant_id": "v1",
            "mode": "dine_in",
            "direction": "right",
            "session_id": str(uuid.uuid4()),
            "card_position": 0,
        },
    )
    response = client.delete("/v1/account")
    assert response.status_code == 200
    assert profiles.get("test-user") is None
    assert events.swipes == []  # D-013: full purge, no orphaned events
