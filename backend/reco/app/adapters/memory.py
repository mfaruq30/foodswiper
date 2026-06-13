"""In-memory adapters: the $0 demo backend and the test fakes — same code.

1,600 venues fit comfortably in RAM, so an ndjson-backed in-process repository
is a legitimate serving path for the free MVP-1 demo (zero Firestore reads),
not just a test double. Selected with MUNCH_BACKEND=memory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..filters import hard_filter
from ..models import OpenState, RequestContext, Restaurant, UserProfile
from ..ports import (
    ConversionEvent,
    FeedbackEvent,
    ServedDeck,
    StoredProfile,
    SwipeEvent,
)


def restaurant_from_canonical(record: dict[str, Any]) -> Restaurant:
    """Map one canonical venues.ndjson record to the domain type.

    The ndjson schema is the backend-neutral contract (D-019): both this
    adapter and the Firestore writer consume it, so the mapping lives in one
    place per consumer and the seed pipeline never emits backend specifics.
    open_state is UNKNOWN until the hours parser lands (FUTURE(Phase 5),
    D-010) — uniform across venues, so the scorer's penalty cancels out.
    """
    return Restaurant(
        id=str(record["id"]),
        name=str(record["name"]),
        cuisines=[str(c) for c in record.get("cuisines", [])],
        price_tier=int(record.get("price_tier", 2)),
        price_imputed=bool(record.get("price_imputed", True)),
        lat=float(record["lat"]),
        lon=float(record["lon"]),
        metro=str(record["metro"]),
        dietary_tags=[str(t) for t in record.get("dietary_tags", [])],
        open_state=OpenState.UNKNOWN,
        phone=record.get("phone"),
        popularity_prior=float(record.get("popularity_prior", 0.0)),
        internal_score=None,
        internal_impressions=0,
        internal_rights=0,
    )


class InMemoryVenueRepository:
    """VenueRepository over a list of Restaurants (ndjson-loaded or injected)."""

    def __init__(self, venues: list[Restaurant]) -> None:
        self._venues = venues
        self._by_id = {v.id: v for v in venues}

    @classmethod
    def from_ndjson(cls, path: Path) -> InMemoryVenueRepository:
        with path.open(encoding="utf-8") as fh:
            records = [json.loads(line) for line in fh if line.strip()]
        return cls([restaurant_from_canonical(r) for r in records])

    def find_candidates(self, ctx: RequestContext) -> list[Restaurant]:
        # Retrieval is profile-independent (an empty profile here), mirroring
        # what a database range query can actually do. The CALLER (post_deck)
        # owns re-applying the user's dietary/price constraints — see the
        # hard_filter call in main.py.
        return hard_filter(self._venues, UserProfile(), ctx)

    def get_by_ids(self, ids: list[str]) -> list[Restaurant]:
        return [self._by_id[i] for i in ids if i in self._by_id]

    def search_by_name(self, metro: str, query: str, limit: int) -> list[Restaurant]:
        # PREFIX-only on purpose: Firestore can only do prefix scans, and the
        # demo must not promise search semantics production cannot deliver —
        # the weaker contract is the contract (Phase 3 review).
        needle = query.strip().lower()
        if not needle:
            return []
        matches = [
            v for v in self._venues if v.metro == metro and v.name.lower().startswith(needle)
        ]
        matches.sort(key=lambda v: v.name.lower())
        return matches[:limit]


class InMemoryProfileStore:
    """ProfileStore over a dict."""

    def __init__(self) -> None:
        self._profiles: dict[str, StoredProfile] = {}

    def get(self, uid: str) -> StoredProfile | None:
        return self._profiles.get(uid)

    def upsert(self, profile: StoredProfile) -> None:
        self._profiles[profile.uid] = profile

    def delete(self, uid: str) -> None:
        self._profiles.pop(uid, None)


class InMemoryAppleTokenStore:
    """AppleTokenStore over a dict — tests + the demo (where it stays empty)."""

    def __init__(self) -> None:
        self._tokens: dict[str, str] = {}

    def set(self, uid: str, refresh_token: str) -> None:
        self._tokens[uid] = refresh_token

    def get(self, uid: str) -> str | None:
        return self._tokens.get(uid)

    def delete(self, uid: str) -> None:
        self._tokens.pop(uid, None)


class InMemoryReasonCache:
    """ReasonCache over a dict; empty by default — the $0 demo path where
    every card keeps its templated reason. Tests pre-seed it to exercise the
    cached-LLM override."""

    def __init__(self, entries: dict[tuple[str, str, str], str] | None = None) -> None:
        self._entries = entries or {}

    def get_many(self, keys: list[tuple[str, str, str]]) -> dict[tuple[str, str, str], str]:
        return {key: self._entries[key] for key in keys if key in self._entries}


class InMemoryEventLog:
    """EventLog over lists — also what API tests assert against."""

    def __init__(self) -> None:
        self.swipes: list[SwipeEvent] = []
        self.conversions: list[ConversionEvent] = []
        self.feedback: list[FeedbackEvent] = []
        self.decks: list[ServedDeck] = []

    def record_swipe(self, event: SwipeEvent) -> None:
        self.swipes.append(event)

    def record_conversion(self, event: ConversionEvent) -> None:
        self.conversions.append(event)

    def record_feedback(self, event: FeedbackEvent) -> None:
        self.feedback.append(event)

    def record_served_deck(self, deck: ServedDeck) -> None:
        self.decks.append(deck)

    def delete_user_events(self, uid: str) -> None:
        # Full purge on account deletion (D-013 privacy promise).
        self.swipes = [e for e in self.swipes if e.uid != uid]
        self.conversions = [e for e in self.conversions if e.uid != uid]
        self.feedback = [e for e in self.feedback if e.uid != uid]
        self.decks = [d for d in self.decks if d.uid != uid]
