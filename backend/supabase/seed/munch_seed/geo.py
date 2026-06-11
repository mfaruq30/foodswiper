"""Small geographic helpers (pure functions, unit-tested)."""

import math

_EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters. Accurate to ~0.5% — far better than
    the 75-120m thresholds it gates."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def grid_key(lat: float, lon: float, cell_deg: float = 0.001) -> tuple[int, int]:
    """Bucket a coordinate into a ~111m grid cell for neighbor lookups."""
    return (int(lat / cell_deg), int(lon / cell_deg))


def neighbor_keys(key: tuple[int, int]) -> list[tuple[int, int]]:
    """The 3x3 neighborhood around a grid cell (covers edge-straddling points)."""
    r, c = key
    return [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]
