"""Taste archetypes — the cache key that makes LLM reasons affordable (D-004).

An LLM reason for a venue depends on the venue + the user's broad taste + the
mode. Keying the cache on the EXACT user would mean one generation per user per
venue (millions). Keying on a coarse ARCHETYPE — the user's top cuisines — means
one generation per (venue, archetype, mode), reused across everyone who shares
that taste. A pure, deterministic function so the same taste always hits the
same cache row.
"""

from __future__ import annotations

from .models import UserProfile
from .scoring import cuisine_weights_for_user

# How many top cuisines define an archetype. Two is coarse enough to collapse
# users into a few hundred archetypes, specific enough that a reason written
# for it still feels personal.
_ARCHETYPE_CUISINE_COUNT = 2


def archetype_key(user: UserProfile) -> str:
    """A stable, low-cardinality taste key, e.g. "italian+ramen" or "new"."""
    weights = cuisine_weights_for_user(user)
    if not weights:
        return "new"  # cold-start users share one archetype
    # Highest-weighted cuisines, ties broken alphabetically for determinism.
    top = sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))[:_ARCHETYPE_CUISINE_COUNT]
    return "+".join(cuisine for cuisine, _ in top)
