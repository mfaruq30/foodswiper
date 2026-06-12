"""Layer 2 — heuristic scorer (spec §7.3).

An explainable weighted sum that works from swipe #1, because the cold-start
signal (cuisine affinity from anchors) carries it before any learned model
exists. Every term is in [0, 1]; the weights (config) are a convex combination
so the final score is in [0, 1] and comparable across users and decks.
"""

from __future__ import annotations

from .config import DEFAULT_CONFIG, ScoringConfig
from .cuisine_affinity import affinity
from .geo import haversine_m
from .models import OpenState, RequestContext, Restaurant, ScoredCandidate, UserProfile

# Recency decay for the running list of right-swiped cuisines: the most recent
# right-swipe weighs 1.0, the next 0.85, and so on. Recent taste signal should
# outweigh stale signal without erasing it.
_RECENT_DECAY = 0.85


def _clamp01(value: float) -> float:
    """Clamp to [0, 1].

    Used at the trust boundary where externally-supplied data (a persisted
    score, an open-data prior, a cuisine weight) enters the composite. The
    docstrings promise every term is in [0, 1]; this makes that a guarantee
    rather than a convention a Phase-3 data adapter could violate.
    """
    return min(1.0, max(0.0, value))


def beta_smoothed_score(rights: int, impressions: int, mean: float, strength: float) -> float:
    """Bayesian-smoothed right-swipe rate (DECISIONS.md D-009).

    Pulls a venue's observed rate toward the global prior in proportion to how
    little evidence it has, so 1/1 (a single lucky impression) cannot outrank
    45/60. `strength` is the prior's weight in effective impressions.
    """
    alpha = mean * strength
    beta = (1.0 - mean) * strength
    return (rights + alpha) / (impressions + alpha + beta)


def _weighted_recent_cuisines(recent_right_cuisines: list[str]) -> dict[str, float]:
    """Collapse a recency-ordered cuisine list into decayed weights in [0, 1]."""
    weights: dict[str, float] = {}
    for index, cuisine in enumerate(recent_right_cuisines):
        weights[cuisine] = max(weights.get(cuisine, 0.0), _RECENT_DECAY**index)
    return weights


def _cuisine_weights_for_user(user: UserProfile) -> dict[str, float]:
    """Static taste prior: explicit onboarding weights, or anchors at full weight."""
    if user.cuisine_weights:
        return user.cuisine_weights
    return {cuisine: 1.0 for cuisine in user.anchor_cuisines}


def price_fit(restaurant: Restaurant, user: UserProfile, config: ScoringConfig) -> float:
    """1.0 when the venue's tier matches the user's preference, falling to 0.

    With no stated preference the term is neutral (0.5). An imputed tier is
    blended toward neutral so a guessed price can neither reward nor punish
    strongly (D-010).
    """
    if user.price_pref is None:
        return 0.5
    raw = 1.0 - abs(restaurant.price_tier - user.price_pref) / 3.0
    if restaurant.price_imputed:
        # Blend toward neutral by the configured imputed weight.
        return 0.5 + (raw - 0.5) * config.imputed_price_weight
    return raw


def proximity_score(restaurant: Restaurant, ctx: RequestContext) -> float:
    """Closer is better, linear to the range edge. For delivery this distance
    is the lawful free proxy for ETA (no provider API exists — D-010)."""
    # A non-positive radius is a degenerate request (e.g. a bad client param);
    # score 0 rather than divide by zero. score_candidate is callable on its own,
    # so this cannot lean on passes_range having run upstream.
    if ctx.max_distance_m <= 0:
        return 0.0
    distance = haversine_m(ctx.user_lat, ctx.user_lon, restaurant.lat, restaurant.lon)
    return max(0.0, 1.0 - distance / ctx.max_distance_m)


def quality_score(restaurant: Restaurant, config: ScoringConfig) -> float:
    """Munch-owned swipe signal once it exists, else the open-data prior.

    Precedence (DECISIONS.md D-009): a precomputed `internal_score` — the
    weekly-recomputed, decayed Beta posterior the data layer persists — wins
    when present; otherwise the posterior is recomputed live from raw counts;
    otherwise the open-data popularity prior carries cold start. Preferring the
    stored value closes a Phase-3 trap: a Firestore adapter that populates
    `internal_score` would otherwise have zero ranking effect. Never a scraped
    third-party rating — this is the moat (spec §7.3).
    """
    if restaurant.internal_score is not None:
        return _clamp01(restaurant.internal_score)
    if restaurant.internal_impressions > 0:
        return beta_smoothed_score(
            restaurant.internal_rights,
            restaurant.internal_impressions,
            config.score_prior_mean,
            config.score_prior_strength,
        )
    return _clamp01(restaurant.popularity_prior)


def score_candidate(
    restaurant: Restaurant,
    user: UserProfile,
    ctx: RequestContext,
    config: ScoringConfig = DEFAULT_CONFIG,
) -> ScoredCandidate:
    """Compute the full heuristic score with its per-signal breakdown."""
    weights = config.weights
    components = {
        "cuisine_affinity": affinity(_cuisine_weights_for_user(user), restaurant.cuisines),
        "swipe_pattern_match": affinity(
            _weighted_recent_cuisines(user.recent_right_cuisines), restaurant.cuisines
        ),
        "price_fit": price_fit(restaurant, user, config),
        "proximity": proximity_score(restaurant, ctx),
        "quality_prior": quality_score(restaurant, config),
    }
    base = (
        weights.cuisine_affinity * components["cuisine_affinity"]
        + weights.swipe_pattern_match * components["swipe_pattern_match"]
        + weights.price_fit * components["price_fit"]
        + weights.proximity * components["proximity"]
        + weights.quality_prior * components["quality_prior"]
    )
    # Unknown-hours venues are surfaced but ranked below known-open ones (D-010).
    if restaurant.open_state is OpenState.UNKNOWN:
        base *= config.unknown_hours_penalty
    return ScoredCandidate(restaurant=restaurant, score=base, components=components)


class HeuristicRanker:
    """The Layer-2 ranker: filter-survivors in, scored order out.

    This is the designated champion until a learned ranker beats it on REAL
    logged swipes (DECISIONS.md D-007) — never on the synthetic harness alone.
    """

    version = "heuristic-v1"

    def __init__(self, config: ScoringConfig = DEFAULT_CONFIG) -> None:
        self._config = config

    def rank(
        self, user: UserProfile, ctx: RequestContext, candidates: list[Restaurant]
    ) -> list[Restaurant]:
        scored = [score_candidate(c, user, ctx, self._config) for c in candidates]
        scored.sort(key=lambda s: s.score, reverse=True)
        return [s.restaurant for s in scored]
