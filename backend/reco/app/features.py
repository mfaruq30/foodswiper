"""Feature extraction for the learned ranker (Layer 4, spec §7.5).

ONE feature function, shared by training and serving — if training and serving
ever computed features differently, the learned model would be silently wrong
(train/serve skew, the classic ML production bug). Pure Python, no LightGBM
dependency, so it imports and tests anywhere.

Every feature is a plain float. The order is FROZEN: `FEATURE_NAMES` is the
contract a trained model is bound to, so append-only — never reorder or
remove, or an old model reads garbage. Bump nothing here without retraining.
"""

from __future__ import annotations

import math

from .config import DEFAULT_CONFIG, ScoringConfig
from .cuisine_affinity import affinity
from .geo import haversine_m
from .models import OpenState, RequestContext, Restaurant, UserProfile
from .scoring import (
    beta_smoothed_score,
    cuisine_weights_for_user,
    price_fit,
    proximity_score,
    quality_score,
    weighted_recent_cuisines,
)

# Frozen, ordered feature contract. Append-only.
FEATURE_NAMES: tuple[str, ...] = (
    "cuisine_affinity",  # the Layer-2 static-taste signal
    "swipe_pattern_match",  # the Layer-2 dynamic-taste signal
    "price_fit",  # the Layer-2 price signal
    "proximity",  # the Layer-2 distance signal
    "quality_prior",  # the Layer-2 quality signal
    "distance_norm",  # raw distance / radius (proximity's inverse, unclamped shape)
    "price_tier_norm",  # tier in [0.25, 1.0]
    "price_imputed",  # 1.0 when the tier is a guess (D-010)
    "price_delta",  # |tier - pref| / 3, or 0.5 when no pref
    "impressions_log",  # log1p(impressions) normalized — evidence volume
    "internal_rate",  # raw right/impressions, or prior mean when cold
    "popularity_prior",  # open-data cold-start prior
    "cuisine_breadth",  # min(#cuisines, 5)/5 — how multi-tagged
    "is_anchor_cuisine",  # 1.0 when a candidate cuisine is a user anchor
    "recent_overlap",  # fraction of recent right-swipe cuisines hit
    "hours_unknown",  # 1.0 when open_state is UNKNOWN (D-010)
)

# Normalizer for the impressions-volume feature: ~1000 impressions saturates.
_IMPRESSIONS_SATURATION = math.log1p(1000.0)


def extract_features(
    restaurant: Restaurant,
    user: UserProfile,
    ctx: RequestContext,
    config: ScoringConfig = DEFAULT_CONFIG,
) -> list[float]:
    """Map one (candidate, user, context) to the frozen feature vector.

    Reuses the Layer-2 component functions verbatim so the learned ranker is
    a strict superset of the heuristic's information — it can recover the
    heuristic exactly and only add lift by weighting/combining better.
    """
    static_weights = cuisine_weights_for_user(user)
    recent_weights = weighted_recent_cuisines(user.recent_right_cuisines)
    anchors = set(user.anchor_cuisines) | set(user.cuisine_weights)

    distance = haversine_m(ctx.user_lat, ctx.user_lon, restaurant.lat, restaurant.lon)
    # NOTE (D-023 pre-promotion item #2): distance_norm and proximity both scale
    # by the request radius, so the synthetic trainer's fixed 8000m radius
    # shifts these features vs the variable serve radius. Latent (the challenger
    # never serves); real-data training on logged radii resolves it.
    distance_norm = distance / ctx.max_distance_m if ctx.max_distance_m > 0 else 1.0

    if user.price_pref is None:
        price_delta = 0.5
    else:
        price_delta = abs(restaurant.price_tier - user.price_pref) / 3.0

    if restaurant.internal_impressions > 0:
        internal_rate = restaurant.internal_rights / restaurant.internal_impressions
    else:
        internal_rate = config.score_prior_mean

    recent_overlap = 0.0
    if recent_weights:
        hit = sum(1 for c in restaurant.cuisines if c in recent_weights)
        recent_overlap = hit / len(recent_weights)

    return [
        affinity(static_weights, restaurant.cuisines),
        affinity(recent_weights, restaurant.cuisines),
        price_fit(restaurant, user, config),
        proximity_score(restaurant, ctx),
        quality_score(restaurant, config),
        min(distance_norm, 2.0),
        restaurant.price_tier / 4.0,
        1.0 if restaurant.price_imputed else 0.0,
        price_delta,
        min(math.log1p(restaurant.internal_impressions) / _IMPRESSIONS_SATURATION, 1.0),
        beta_smoothed_score(
            restaurant.internal_rights,
            restaurant.internal_impressions,
            config.score_prior_mean,
            config.score_prior_strength,
        )
        if restaurant.internal_impressions > 0
        else internal_rate,
        max(0.0, min(1.0, restaurant.popularity_prior)),
        min(len(restaurant.cuisines), 5) / 5.0,
        1.0 if anchors & set(restaurant.cuisines) else 0.0,
        recent_overlap,
        1.0 if restaurant.open_state is OpenState.UNKNOWN else 0.0,
    ]
