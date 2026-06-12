"""Firestore adapter logic over a minimal fake client.

The real client needs credentials/emulator; this fake implements exactly the
query surface the adapter uses, so the adapter's own logic — range bounds,
prefix sentinel, score merging, post-filtering, delete pagination — is pinned
without any Firebase dependency. (The prefix-sentinel bug this guards against
shipped once already: an end_at of `needle + ""` made /v1/search exact-match
only in production while every test passed on the memory adapter.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.adapters.firestore import FirestoreEventLog, FirestoreVenueRepository
from app.models import Mode, RequestContext
from app.ports import SwipeEvent


@dataclass
class _FakeSnap:
    id: str
    _data: dict[str, Any]
    reference: Any = None

    @property
    def exists(self) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)


@dataclass
class _FakeQuery:
    docs: dict[str, dict[str, Any]]
    filters: list[tuple[str, str, Any]] = field(default_factory=list)
    order_field: str | None = None
    start: Any = None
    end: Any = None
    max_results: int | None = None

    def where(self, *args: Any, **_: Any) -> _FakeQuery:
        f, op, v = args
        return _FakeQuery(
            self.docs,
            [*self.filters, (f, op, v)],
            self.order_field,
            self.start,
            self.end,
            self.max_results,
        )

    def order_by(self, fld: str) -> _FakeQuery:
        return _FakeQuery(self.docs, self.filters, fld, self.start, self.end, self.max_results)

    def start_at(self, doc: dict[str, Any]) -> _FakeQuery:
        assert self.order_field is not None
        return _FakeQuery(
            self.docs,
            self.filters,
            self.order_field,
            doc[self.order_field],
            self.end,
            self.max_results,
        )

    def end_at(self, doc: dict[str, Any]) -> _FakeQuery:
        assert self.order_field is not None
        return _FakeQuery(
            self.docs,
            self.filters,
            self.order_field,
            self.start,
            doc[self.order_field],
            self.max_results,
        )

    def limit(self, n: int) -> _FakeQuery:
        return _FakeQuery(self.docs, self.filters, self.order_field, self.start, self.end, n)

    def stream(self) -> list[_FakeSnap]:
        out = []
        for doc_id, data in self.docs.items():
            keep = True
            for f, op, v in self.filters:
                actual = doc_id if f == "__name__" else data.get(f)
                if (op == "==" and actual != v) or (op == "in" and actual not in v):
                    keep = False
            if not keep:
                continue
            if self.order_field is not None:
                key = data.get(self.order_field)
                if self.start is not None and key < self.start:
                    continue
                if self.end is not None and key > self.end:
                    continue
            out.append(_FakeSnap(doc_id, data))
        if self.order_field is not None:
            order_field = self.order_field  # narrowed for the lambda
            out.sort(key=lambda s: s._data.get(order_field) or "")
        return out[: self.max_results] if self.max_results is not None else out


class _FakeCollection(_FakeQuery):
    def document(self, doc_id: str) -> Any:
        docs = self.docs

        class _Ref:
            id = doc_id

            def get(self) -> Any:
                if doc_id in docs:
                    return _FakeSnap(doc_id, docs[doc_id])

                class _Missing:
                    exists = False
                    id = doc_id

                    def to_dict(self) -> None:
                        return None

                return _Missing()

        return _Ref()


class _FakeBatch:
    def __init__(self, client: _FakeClient) -> None:
        self._client = client
        self.deleted: list[str] = []

    def delete(self, ref: Any) -> None:
        self.deleted.append(ref)
        self._client.deletes.append(ref)

    def commit(self) -> None:
        self._client.commits += 1


class _FakeClient:
    def __init__(self, collections: dict[str, dict[str, dict[str, Any]]]) -> None:
        self._collections = collections
        self.deletes: list[Any] = []
        self.commits = 0

    def collection(self, name: str) -> _FakeCollection:
        return _FakeCollection(self._collections.setdefault(name, {}))

    def batch(self) -> _FakeBatch:
        return _FakeBatch(self)


def _venue_doc(name: str, geohash: str, lat: float, lon: float) -> dict[str, Any]:
    return {
        "name": name,
        "name_lower": name.lower(),
        "cuisines": ["pizza"],
        "price_tier": 2,
        "price_imputed": True,
        "lat": lat,
        "lon": lon,
        "metro": "nyc",
        "dietary_tags": [],
        "popularity_prior": 0.5,
        "geohash": geohash,
        "is_active": True,
    }


def test_search_prefix_sentinel_matches_prefixes_not_exact() -> None:
    from app.geohash import encode

    client = _FakeClient(
        {
            "venues": {
                "a": _venue_doc("Lucali", encode(40.73, -73.99), 40.73, -73.99),
                "b": _venue_doc("Lucciola", encode(40.74, -73.98), 40.74, -73.98),
                "c": _venue_doc("Joe's Pizza", encode(40.73, -73.99), 40.73, -73.99),
            },
            "venue_scores": {},
        }
    )
    repo = FirestoreVenueRepository(client)  # type: ignore[arg-type]
    names = [r.name for r in repo.search_by_name("nyc", "luc", 10)]
    # Both Luc* venues match the prefix range; exact-match-only would return [].
    assert names == ["Lucali", "Lucciola"]


def test_find_candidates_postfilters_and_merges_scores() -> None:
    from app.geohash import encode

    near = _venue_doc("Near", encode(40.7308, -73.9973), 40.7308, -73.9973)
    far = _venue_doc("Far", encode(40.7308, -73.9973), 40.80, -73.90)  # lying geohash
    client = _FakeClient(
        {
            "venues": {"near": near, "far": far},
            "venue_scores": {"near": {"impressions": 40, "rights": 30, "internal_score": 0.7}},
        }
    )
    repo = FirestoreVenueRepository(client)  # type: ignore[arg-type]
    ctx = RequestContext(
        mode=Mode.DINE_IN, metro="nyc", user_lat=40.7308, user_lon=-73.9973, max_distance_m=2000
    )
    found = repo.find_candidates(ctx)
    # The haversine post-filter drops the far venue even though its (corrupt)
    # geohash landed it inside a range — exact distance always wins.
    assert [r.id for r in found] == ["near"]
    assert found[0].internal_impressions == 40 and found[0].internal_score == 0.7


def test_delete_user_events_terminates_and_deletes_all() -> None:
    swipes = {f"s{i}": {"uid": "u1", "restaurant_id": "r", "direction": "right"} for i in range(5)}
    swipes["other"] = {"uid": "u2", "restaurant_id": "r", "direction": "left"}
    client = _FakeClient({"swipes": swipes, "conversions": {}, "feedback": {}, "reco_events": {}})

    # The fake's stream() doesn't mutate state, so emulate deletion by having
    # batch.delete remove from the backing dict (what Firestore does).
    original_batch = client.batch

    def batch_with_removal() -> _FakeBatch:
        b = original_batch()
        original_delete = b.delete

        def delete_and_remove(snap_ref: Any) -> None:
            original_delete(snap_ref)
            swipes.pop(snap_ref.id, None)

        b.delete = delete_and_remove  # type: ignore[assignment, method-assign]
        return b

    client.batch = batch_with_removal  # type: ignore[method-assign]

    log = FirestoreEventLog(client)  # type: ignore[arg-type]

    # Patch snap references: our fake snaps have reference=None; give the
    # adapter what it needs by monkey-patching _FakeQuery.stream output.
    original_stream = _FakeQuery.stream

    def stream_with_refs(self: _FakeQuery) -> list[_FakeSnap]:
        snaps = original_stream(self)
        for snap in snaps:
            snap.reference = type("R", (), {"id": snap.id})()
        return snaps

    _FakeQuery.stream = stream_with_refs  # type: ignore[method-assign]
    try:
        log.delete_user_events("u1")
    finally:
        _FakeQuery.stream = original_stream  # type: ignore[method-assign]

    assert set(swipes) == {"other"}  # u1 purged, u2 untouched — and the loop ended


def test_reason_cache_returns_unexpired_hits_keyed_back_to_tuples() -> None:
    from datetime import UTC, datetime, timedelta

    from app.adapters.firestore import FirestoreReasonCache

    now = datetime.now(UTC)
    client = _FakeClient(
        {
            "reason_cache": {
                # doc id format is "{restaurant_id}|{archetype}|{mode}"
                "osm:node:1|pizza+ramen|dine_in": {
                    "reason": "Your kind of slice",
                    "expires_at": now + timedelta(hours=2),
                },
                "osm:node:2|pizza+ramen|dine_in": {
                    "reason": "Stale — should be filtered",
                    "expires_at": now - timedelta(hours=2),
                },
            }
        }
    )
    cache = FirestoreReasonCache(client)  # type: ignore[arg-type]
    keys = [
        ("osm:node:1", "pizza+ramen", "dine_in"),
        ("osm:node:2", "pizza+ramen", "dine_in"),  # expired
        ("osm:node:3", "pizza+ramen", "dine_in"),  # absent
    ]
    hits = cache.get_many(keys)
    # Only the present, unexpired entry — mapped back to its tuple key.
    assert hits == {("osm:node:1", "pizza+ramen", "dine_in"): "Your kind of slice"}


def test_event_log_writes_required_fields() -> None:
    appended: list[tuple[str, dict[str, Any]]] = []

    class _RecordingClient(_FakeClient):
        def collection(self, name: str) -> Any:
            class _Col:
                @staticmethod
                def add(payload: dict[str, Any]) -> None:
                    appended.append((name, payload))

            return _Col()

    log = FirestoreEventLog(_RecordingClient({}))  # type: ignore[arg-type]
    log.record_swipe(
        SwipeEvent(
            uid="u1",
            restaurant_id="r1",
            mode=Mode.DINE_IN,
            direction="right",
            session_id="s",
            request_id="req",
            card_position=3,
            explore=True,
        )
    )
    collection, payload = appended[0]
    assert collection == "swipes"
    # The D-008 training-label fields must reach the document intact.
    assert payload["request_id"] == "req"
    assert payload["card_position"] == 3 and payload["explore"] is True
    assert "created_at" in payload
