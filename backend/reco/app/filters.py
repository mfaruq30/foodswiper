"""Layer 1 — hard filters (spec §7.2).

Deterministic, fast, fully unit-tested. A candidate that fails any constraint
is removed before scoring ever runs; scoring never has to defend against
out-of-range or dietary-conflicting venues. Each predicate is its own function
so the reason a venue was dropped is always nameable.
"""

from __future__ import annotations

from .geo import haversine_m
from .models import OpenState, RequestContext, Restaurant, UserProfile


def passes_metro(restaurant: Restaurant, ctx: RequestContext) -> bool:
    return restaurant.metro == ctx.metro


def passes_range(restaurant: Restaurant, ctx: RequestContext) -> bool:
    distance = haversine_m(ctx.user_lat, ctx.user_lon, restaurant.lat, restaurant.lon)
    return distance <= ctx.max_distance_m


def passes_open(restaurant: Restaurant) -> bool:
    # Three-state policy (D-010): only a definite CLOSED is filtered out.
    # UNKNOWN passes here and is penalized later in scoring, so sparse-hours
    # venues are surfaced (with a badge) rather than silently deleted.
    return restaurant.open_state is not OpenState.CLOSED


def passes_dietary(restaurant: Restaurant, user: UserProfile) -> bool:
    # Every dietary flag the user requires must be present on the venue.
    return all(flag in restaurant.dietary_tags for flag in user.dietary_flags)


def passes_price(restaurant: Restaurant, ctx: RequestContext) -> bool:
    if ctx.price_ceiling is None:
        return True
    # Permissive-on-imputed (D-010): OSM has no price data, so an imputed tier
    # is a guess and must never hard-filter a venue out. Only a real,
    # source-backed price tier can exceed the ceiling.
    if restaurant.price_imputed:
        return True
    return restaurant.price_tier <= ctx.price_ceiling


def hard_filter(
    candidates: list[Restaurant], user: UserProfile, ctx: RequestContext
) -> list[Restaurant]:
    """Return only the candidates that satisfy every mode constraint."""
    return [
        candidate
        for candidate in candidates
        if passes_metro(candidate, ctx)
        and passes_range(candidate, ctx)
        and passes_open(candidate)
        and passes_dietary(candidate, user)
        and passes_price(candidate, ctx)
    ]
