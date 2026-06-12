"""Deterministic, templated reason lines — the always-available fallback.

The product's signature moment is the one-line "why this card" (spec §1).
Phase 5 layers cached LLM-written reasons on top (D-004); this module is the
default path and the degraded mode that keeps the $0 demo fully functional
with no Anthropic key. Templates draw only on facts the card itself shows, so
a reason can never contradict the card.
"""

from __future__ import annotations

from .cuisine_affinity import pair_affinity
from .geo import haversine_m
from .models import RequestContext, Restaurant, UserProfile

# Display names for canonical cuisine nodes that aren't title-case-able.
_CUISINE_LABEL = {
    "bbq": "BBQ",
    "bubble_tea": "bubble tea",
    "middle_eastern": "Middle Eastern",
    "pan_asian": "pan-Asian",
    "korean_bbq": "Korean BBQ",
    "eastern_european": "Eastern European",
}


def _label(cuisine: str) -> str:
    return _CUISINE_LABEL.get(cuisine, cuisine.replace("_", " ").title())


def _miles(meters: float) -> str:
    return f"{meters / 1609.34:.1f} mi"


def templated_reason(restaurant: Restaurant, user: UserProfile, ctx: RequestContext) -> str:
    """The strongest honest claim available, in priority order:
    taste match > taste adjacency > proven crowd signal > proximity."""
    distance = _miles(haversine_m(ctx.user_lat, ctx.user_lon, restaurant.lat, restaurant.lon))
    loved = list(user.cuisine_weights) or user.anchor_cuisines

    direct = next((c for c in restaurant.cuisines if c in loved), None)
    if direct:
        return f"You love {_label(direct)} — this one's {distance} away"

    for user_cuisine in loved:
        neighbor = next(
            (c for c in restaurant.cuisines if pair_affinity(user_cuisine, c) >= 0.6), None
        )
        if neighbor:
            return f"Into {_label(user_cuisine)}? {_label(neighbor)} is a close cousin — {distance}"

    if restaurant.internal_score is not None and restaurant.internal_score >= 0.6:
        percent = round(restaurant.internal_score * 100)
        return f"{percent}% of people with your taste liked this — {distance} away"

    primary = _label(restaurant.cuisines[0]) if restaurant.cuisines else "A local spot"
    return f"{primary} worth a look, just {distance} from you"
