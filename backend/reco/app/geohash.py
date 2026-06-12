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

import math

from .geo import haversine_m

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

# Conservative meters-per-degree constants. Latitude varies 110.57-111.69 km
# per degree; using the MINIMUM means we always under-estimate cell size,
# which errs toward coarser precision = MORE coverage (the safe direction).
_M_PER_DEG_LAT = 110_540.0
_M_PER_DEG_LON_EQ = 111_320.0

ENCODE_PRECISION = 9  # ~5 m cells: precise enough to sort venues stably.


def _min_cell_dimension_m(precision: int, lat: float) -> float:
    """The SMALLER side of a geohash cell at this precision and latitude.

    Why the smaller side, computed at the query latitude: the coverage
    guarantee requires a single cell to be at least radius-sized in EVERY
    direction. A precision's longitude width shrinks by cos(latitude)
    (~0.76 at NYC), and odd/even precisions split their bits unevenly between
    the axes — an earlier version used a static equator-width table and
    silently dropped up to ~24% of in-radius venues for some client radii
    (D-021). Geohash bit split: 5 bits/char, alternating lon-first.
    """
    bits = 5 * precision
    lat_bits = bits // 2
    lon_bits = bits - lat_bits
    lat_height = (180.0 / (1 << lat_bits)) * _M_PER_DEG_LAT
    lon_width = (
        (360.0 / (1 << lon_bits)) * _M_PER_DEG_LON_EQ * math.cos(math.radians(min(abs(lat), 89.9)))
    )
    return min(lat_height, lon_width)


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
    """Inclusive prefix ranges covering a radius around a point.

    Each range queries one cell of the 3x3 neighborhood at the finest precision
    whose cell is still at least radius-sized in its SMALLER dimension at this
    latitude — so the neighborhood provably covers the circle (D-021). The end
    bound is prefix + '~', which sorts above every real geohash extension
    ('z' < '~' in ASCII). Callers MUST post-filter with haversine: cells
    overshoot the circle by design (up to ~100x area at unlucky radii — a read
    cost, never a correctness issue; cost numbers recorded in D-021).
    """
    if radius_m > _min_cell_dimension_m(1, lat):
        # Guard locally rather than trusting callers' clamps: beyond one
        # precision-1 cell the 3x3 guarantee is void.
        raise ValueError(f"radius {radius_m} m exceeds geohash coverage guarantee")
    precision = 1
    for p in range(1, 10):
        if _min_cell_dimension_m(p, lat) >= radius_m:
            precision = p
        else:
            break
    center = encode(lat, lon, precision)
    return [(cell, cell + "~") for cell in _neighbors(center)]


def covers(lat: float, lon: float, radius_m: float, venue_lat: float, venue_lon: float) -> bool:
    """The mandatory post-filter: exact distance check after the range scan."""
    return haversine_m(lat, lon, venue_lat, venue_lon) <= radius_m
