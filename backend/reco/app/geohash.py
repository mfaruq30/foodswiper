"""Geohash encoding + radius query bounds (pure Python, fully tested).

Why hand-rolled (~80 lines) instead of a dependency: the geofire-style bounds
logic is the load-bearing half and no maintained typed package provides both
halves; owning it keeps mypy --strict clean and the algorithm auditable.

How retrieval works on Firestore (D-019): each venue stores `geohash` (base32,
precision 9). `query_bounds(center, radius)` returns a handful of [start, end)
prefix ranges at a precision chosen from the radius; the adapter runs one
ordered range query per bound, then discards false positives with the exact
haversine — geohash boxes overshoot a circle by design, so the post-filter is
mandatory, not defensive.
"""

from __future__ import annotations

from .geo import haversine_m

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

# Worst-case cell dimensions (meters) per geohash precision, equator-ish.
# Used to pick the coarsest precision whose cell still covers the radius from
# a 3x3 neighborhood — coarser cells = fewer range queries, more post-filtering.
_CELL_M = {
    1: 5_000_000.0,
    2: 1_250_000.0,
    3: 156_000.0,
    4: 39_100.0,
    5: 4_890.0,
    6: 1_220.0,
    7: 153.0,
    8: 38.2,
}

ENCODE_PRECISION = 9  # ~5 m cells: precise enough to sort venues stably.


def encode(lat: float, lon: float, precision: int = ENCODE_PRECISION) -> str:
    """Standard geohash base32 encoding."""
    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    out: list[str] = []
    bit, ch, even = 0, 0, True
    while len(out) < precision:
        if even:
            mid = (lon_lo + lon_hi) / 2
            if lon >= mid:
                ch = (ch << 1) | 1
                lon_lo = mid
            else:
                ch <<= 1
                lon_hi = mid
        else:
            mid = (lat_lo + lat_hi) / 2
            if lat >= mid:
                ch = (ch << 1) | 1
                lat_lo = mid
            else:
                ch <<= 1
                lat_hi = mid
        even = not even
        bit += 1
        if bit == 5:
            out.append(_BASE32[ch])
            bit, ch = 0, 0
    return "".join(out)


def _decode_cell(geohash: str) -> tuple[float, float, float, float]:
    """Return the (lat_lo, lat_hi, lon_lo, lon_hi) box of a geohash cell."""
    lat_lo, lat_hi = -90.0, 90.0
    lon_lo, lon_hi = -180.0, 180.0
    even = True
    for char in geohash:
        value = _BASE32.index(char)
        for shift in range(4, -1, -1):
            bit = (value >> shift) & 1
            if even:
                mid = (lon_lo + lon_hi) / 2
                if bit:
                    lon_lo = mid
                else:
                    lon_hi = mid
            else:
                mid = (lat_lo + lat_hi) / 2
                if bit:
                    lat_lo = mid
                else:
                    lat_hi = mid
            even = not even
    return lat_lo, lat_hi, lon_lo, lon_hi


def _neighbors(geohash: str) -> list[str]:
    """The 3x3 neighborhood around a cell, computed by re-encoding offset
    center points (simpler and safer than the classic border-lookup tables)."""
    lat_lo, lat_hi, lon_lo, lon_hi = _decode_cell(geohash)
    lat_c, lon_c = (lat_lo + lat_hi) / 2, (lon_lo + lon_hi) / 2
    d_lat, d_lon = lat_hi - lat_lo, lon_hi - lon_lo
    cells = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            lat = min(90.0, max(-90.0, lat_c + dy * d_lat))
            lon = lon_c + dx * d_lon
            if lon > 180.0:
                lon -= 360.0
            if lon < -180.0:
                lon += 360.0
            cells.append(encode(lat, lon, len(geohash)))
    # Order-preserving dedupe (poles/antimeridian can collapse neighbors).
    return list(dict.fromkeys(cells))


def query_bounds(lat: float, lon: float, radius_m: float) -> list[tuple[str, str]]:
    """Prefix ranges [start, end) covering a radius around a point.

    Each range queries one cell of the 3x3 neighborhood at a precision where a
    single cell is at least as large as the radius — so the neighborhood is
    guaranteed to cover the circle. Callers MUST post-filter with haversine.
    """
    precision = 1
    for p in sorted(_CELL_M):
        if _CELL_M[p] >= radius_m:
            precision = p
        else:
            break
    center = encode(lat, lon, precision)
    return [(cell, cell + "~") for cell in _neighbors(center)]  # '~' > 'z' in ASCII


def covers(lat: float, lon: float, radius_m: float, venue_lat: float, venue_lon: float) -> bool:
    """The mandatory post-filter: exact distance check after the range scan."""
    return haversine_m(lat, lon, venue_lat, venue_lon) <= radius_m
