"""Firestore adapters (D-019): the production backend for project food-5eb2a.

Geospatial retrieval = geohash range queries (app.geohash.query_bounds) plus
the mandatory exact-haversine post-filter — Firestore has no native radius
query. Requires the composite index (metro ASC, is_active ASC, geohash ASC);
declared in firestore.indexes.json at the repo root.

Collections (mirrors DATA_MODEL.md, Firestore edition):
  venues/{id}            — canonical venue docs (from venues.ndjson)
  venue_scores/{id}      — Munch-owned swipe counters + decayed posterior
  profiles/{uid}         — taste profiles
  swipes, conversions, feedback, reco_events — append-only event docs

Clients NEVER touch these collections (deny-all rules): all access flows
through this Admin-SDK adapter inside the API, which is what makes the
backend swappable (D-019 seam).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any, cast

from ..geohash import covers, query_bounds
from ..models import OpenState, RequestContext, Restaurant
from ..ports import (
    ConversionEvent,
    FeedbackEvent,
    ServedDeck,
    StoredProfile,
    SwipeEvent,
)

if TYPE_CHECKING:
    from google.cloud import firestore
    from google.cloud.firestore import DocumentSnapshot


def _get_sync(ref: Any) -> DocumentSnapshot:
    """Narrow the library's sync/async union at the boundary: the sync Client
    always returns a concrete snapshot; the Awaitable arm exists only for the
    async client. `Any` because the stubs disagree with themselves about
    whether document() yields DocumentReference or BaseDocumentReference."""
    return cast("DocumentSnapshot", ref.get())


def _to_restaurant(doc_id: str, data: dict[str, Any]) -> Restaurant:
    """Venue doc -> domain type. Scores arrive via a separate merge step."""
    return Restaurant(
        id=doc_id,
        name=str(data["name"]),
        cuisines=[str(c) for c in data.get("cuisines", [])],
        price_tier=int(data.get("price_tier", 2)),
        price_imputed=bool(data.get("price_imputed", True)),
        lat=float(data["lat"]),
        lon=float(data["lon"]),
        metro=str(data["metro"]),
        dietary_tags=[str(t) for t in data.get("dietary_tags", [])],
        open_state=OpenState.UNKNOWN,  # hours parser is FUTURE(Phase 5), D-010
        phone=data.get("phone"),
        popularity_prior=float(data.get("popularity_prior", 0.0)),
    )


class FirestoreVenueRepository:
    """VenueRepository over Firestore geohash range queries."""

    def __init__(self, client: firestore.Client) -> None:
        self._db = client

    def _merge_scores(self, venues: list[Restaurant]) -> list[Restaurant]:
        """Attach venue_scores counters so ranking sees the swipe signal.

        Fetched in chunks of 30 (Firestore's `in` query limit) — candidate sets
        are bounded by the deck pipeline, so this is a handful of reads.
        """
        ids = [v.id for v in venues]
        scores: dict[str, dict[str, Any]] = {}
        for start in range(0, len(ids), 30):
            chunk = ids[start : start + 30]
            query = self._db.collection("venue_scores").where("__name__", "in", chunk)
            for snap in query.stream():
                scores[snap.id] = snap.to_dict() or {}
        for venue in venues:
            score = scores.get(venue.id)
            if score:
                venue.internal_impressions = int(score.get("impressions", 0))
                venue.internal_rights = int(score.get("rights", 0))
                raw = score.get("internal_score")
                venue.internal_score = float(raw) if raw is not None else None
        return venues

    def find_candidates(self, ctx: RequestContext) -> list[Restaurant]:
        seen: dict[str, Restaurant] = {}
        for lo, hi in query_bounds(ctx.user_lat, ctx.user_lon, ctx.max_distance_m):
            query = (
                self._db.collection("venues")
                .where("metro", "==", ctx.metro)
                .where("is_active", "==", True)
                .order_by("geohash")
                .start_at({"geohash": lo})
                .end_at({"geohash": hi})
            )
            for snap in query.stream():
                data = snap.to_dict() or {}
                # Geohash boxes overshoot the circle — exact check is mandatory.
                if covers(ctx.user_lat, ctx.user_lon, ctx.max_distance_m, data["lat"], data["lon"]):
                    seen[snap.id] = _to_restaurant(snap.id, data)
        return self._merge_scores(list(seen.values()))

    def get_by_ids(self, ids: list[str]) -> list[Restaurant]:
        out: list[Restaurant] = []
        for venue_id in ids:
            snap = _get_sync(self._db.collection("venues").document(venue_id))
            if snap.exists:
                out.append(_to_restaurant(snap.id, snap.to_dict() or {}))
        return self._merge_scores(out)

    def search_by_name(self, metro: str, query: str, limit: int) -> list[Restaurant]:
        # Prefix search over the seed-written name_lower field — Firestore has
        # no substring queries; prefix is what autocomplete needs anyway.
        needle = query.strip().lower()
        if not needle:
            return []
        snaps = (
            self._db.collection("venues")
            .where("metro", "==", metro)
            .where("is_active", "==", True)
            .order_by("name_lower")
            .start_at({"name_lower": needle})
            .end_at({"name_lower": needle + ""})
            .limit(limit)
            .stream()
        )
        return [_to_restaurant(s.id, s.to_dict() or {}) for s in snaps]


class FirestoreProfileStore:
    """ProfileStore over profiles/{uid}."""

    def __init__(self, client: firestore.Client) -> None:
        self._db = client

    def get(self, uid: str) -> StoredProfile | None:
        snap = _get_sync(self._db.collection("profiles").document(uid))
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        return StoredProfile(
            uid=uid,
            display_name=data.get("display_name"),
            home_metro=data.get("home_metro"),
            anchor_cuisines=[str(c) for c in data.get("anchor_cuisines", [])],
            cuisine_weights={str(k): float(v) for k, v in data.get("cuisine_weights", {}).items()},
            price_pref=data.get("price_pref"),
            dietary_flags=[str(f) for f in data.get("dietary_flags", [])],
            recent_right_cuisines=[str(c) for c in data.get("recent_right_cuisines", [])],
        )

    def upsert(self, profile: StoredProfile) -> None:
        data = asdict(profile)
        data.pop("uid")
        self._db.collection("profiles").document(profile.uid).set(data)

    def delete(self, uid: str) -> None:
        self._db.collection("profiles").document(uid).delete()


class FirestoreEventLog:
    """EventLog over append-only event collections."""

    def __init__(self, client: firestore.Client) -> None:
        self._db = client

    def _append(self, collection: str, payload: dict[str, Any]) -> None:
        from google.cloud.firestore import SERVER_TIMESTAMP

        payload["created_at"] = SERVER_TIMESTAMP
        self._db.collection(collection).add(payload)

    def record_swipe(self, event: SwipeEvent) -> None:
        self._append("swipes", asdict(event))

    def record_conversion(self, event: ConversionEvent) -> None:
        self._append("conversions", asdict(event))

    def record_feedback(self, event: FeedbackEvent) -> None:
        self._append("feedback", asdict(event))

    def record_served_deck(self, deck: ServedDeck) -> None:
        self._append("reco_events", asdict(deck))

    def delete_user_events(self, uid: str) -> None:
        # Full purge on account deletion (D-013). Batched at Firestore's limit.
        for collection in ("swipes", "conversions", "feedback", "reco_events"):
            while True:
                snaps = list(
                    self._db.collection(collection).where("uid", "==", uid).limit(450).stream()
                )
                if not snaps:
                    break
                batch = self._db.batch()
                for snap in snaps:
                    batch.delete(snap.reference)
                batch.commit()


def build_firestore_backend(
    project_id: str,
) -> tuple[FirestoreVenueRepository, FirestoreProfileStore, FirestoreEventLog]:
    """Construct the production adapter set — the ONLY place a Firestore
    client is built, so the composition root (main) never imports
    google.cloud (D-019 seam)."""
    from google.cloud import firestore as fs

    client = fs.Client(project=project_id)
    return (
        FirestoreVenueRepository(client),
        FirestoreProfileStore(client),
        FirestoreEventLog(client),
    )


class FirebaseTokenVerifier:
    """TokenVerifier AND AccountDeleter over firebase_admin.

    Isolated here so the partially-typed firebase_admin package never leaks
    past the ports. Swapping auth providers later = a new TokenVerifier.
    """

    def __init__(self, project_id: str) -> None:
        import firebase_admin

        # Default credentials; idempotent across uvicorn reloads.
        if not firebase_admin._apps:
            firebase_admin.initialize_app(options={"projectId": project_id})

    def verify(self, token: str) -> str:
        from firebase_admin import auth as fb_auth

        from ..auth import AuthError

        try:
            claims = fb_auth.verify_id_token(token)
        except Exception as exc:  # firebase_admin raises a family of types
            raise AuthError(str(exc)) from exc
        return str(claims["uid"])

    def delete_user(self, uid: str) -> None:
        """Remove the Firebase Auth account itself (part of D-013 deletion).

        FUTURE(Phase 6): when Sign in with Apple lands, deletion must ALSO
        revoke the Apple refresh token per TN3194 — the token is captured at
        first sign-in and revoked via Apple's /auth/revoke before this call.
        """
        from firebase_admin import auth as fb_auth

        fb_auth.delete_user(uid)
