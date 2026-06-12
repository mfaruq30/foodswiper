"""Domain types for the recommendation core.

Deliberately database-agnostic: every type here is a plain in-memory value
object. The data-access adapter that fills these from Firestore lives in
Phase 3 — the filters, scorer, and eval harness never know where a candidate
came from, which is why all of Phase 2 survived the Supabase->Firebase pivot
(DECISIONS.md D-019).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Mode(StrEnum):
    """The three discovery modes; each has its own filters and ranking feel."""

    DINE_IN = "dine_in"
    PICKUP = "pickup"
    DELIVERY = "delivery"


class OpenState(StrEnum):
    """Three-state open status (DECISIONS.md D-010).

    UNKNOWN is a first-class value, not a synonym for CLOSED: ~half of OSM
    venues lack hours, and hard-filtering them would silently delete half the
    inventory. UNKNOWN passes the open-now filter with a scoring penalty.
    """

    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class Restaurant:
    """A candidate venue, already resolved to the current request's context.

    `open_state` is computed upstream from `hours` against the request time so
    the filter stays a pure function of this struct.
    """

    id: str
    name: str
    cuisines: list[str]
    price_tier: int  # 1-4
    price_imputed: bool
    lat: float
    lon: float
    metro: str
    dietary_tags: list[str]
    open_state: OpenState
    # Cold-start prior from open data (tag richness + inspection recency).
    popularity_prior: float
    # Munch-owned swipe-derived signal; None until enough impressions exist.
    internal_score: float | None = None
    internal_impressions: int = 0
    internal_rights: int = 0


@dataclass(slots=True)
class UserProfile:
    """A user's persisted taste, assembled from onboarding + swipe history.

    `cuisine_weights` are normalized affinities in [0, 1] keyed by canonical
    cuisine node. `anchor_cuisines` are the cuisines of the restaurants the
    user named at onboarding — the cold-start backbone (spec §7.3).
    """

    cuisine_weights: dict[str, float] = field(default_factory=dict)
    anchor_cuisines: list[str] = field(default_factory=list)
    price_pref: int | None = None
    dietary_flags: list[str] = field(default_factory=list)
    # Cuisines the user has right-swiped this session/recently, most-recent
    # first — drives `swipe_pattern_match`, the dynamic counterpart to the
    # static cuisine affinity.
    recent_right_cuisines: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RequestContext:
    """Everything about the current deck request that the ranker needs."""

    mode: Mode
    metro: str
    user_lat: float
    user_lon: float
    max_distance_m: float
    price_ceiling: int | None = None


@dataclass(slots=True)
class ScoredCandidate:
    """A restaurant plus its heuristic score and per-signal breakdown.

    `components` is kept so the score is explainable end to end — it feeds
    both the eval harness's debugging and (later) the reason generator.
    """

    restaurant: Restaurant
    score: float
    components: dict[str, float]
