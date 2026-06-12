"""Geographic helper (pure, unit-tested).

An intentional independent copy of the seed pipeline's ``haversine_m``
(backend/supabase/seed): the two packages deploy separately with separate
venvs, and reco stays DB-agnostic. There is NO runtime coupling and nothing
enforces the two stay identical — if either is ever tuned, change both
deliberately.
"""

from __future__ import annotations

import math

_EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters; accurate to ~0.5%."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))
