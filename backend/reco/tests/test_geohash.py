"""Geohash encode + radius query bounds — the Firestore retrieval math."""

import math

import pytest

from app.geo import haversine_m
from app.geohash import _decode_cell, covers, encode, query_bounds


def test_encode_reference_point() -> None:
    # Washington Square, Manhattan. 'dr5r' is the well-known NYC geohash
    # prefix; the full value is pinned to catch algorithm drift.
    assert encode(40.7308, -73.9973, 7) == "dr5rsnu"
    # Prefix property: a shorter hash is a prefix of the longer one.
    assert encode(40.7308, -73.9973, 9).startswith("dr5rsnu")


def test_encode_decode_containment() -> None:
    # Independent correctness property (not circular with the encoder): the
    # decoded cell box must contain the encoded point, at every precision.
    for precision in (3, 5, 7, 9):
        geohash = encode(40.7308, -73.9973, precision)
        lat_lo, lat_hi, lon_lo, lon_hi = _decode_cell(geohash)
        assert lat_lo <= 40.7308 <= lat_hi
        assert lon_lo <= -73.9973 <= lon_hi


def test_encode_is_monotone_in_proximity() -> None:
    # Two points meters apart share a long prefix; cross-town points do not.
    a = encode(40.7308, -73.9973)
    b = encode(40.7309, -73.9974)  # ~15 m away
    far = encode(40.8000, -73.9000)  # ~8 km away
    assert a[:6] == b[:6]
    assert a[:4] != far[:4] or a[:5] != far[:5]


def _destination(
    lat: float, lon: float, bearing_deg: float, distance_m: float
) -> tuple[float, float]:
    """Great-circle destination point — proper spherical math, because the flat
    deg = m/111320 approximation under-probes east-west (ignores cos(lat))."""
    radius_earth = 6_371_000.0
    bearing = math.radians(bearing_deg)
    phi1, lam1 = math.radians(lat), math.radians(lon)
    delta = distance_m / radius_earth
    phi2 = math.asin(
        math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(bearing)
    )
    lam2 = lam1 + math.atan2(
        math.sin(bearing) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2),
    )
    return math.degrees(phi2), math.degrees(lam2)


@pytest.mark.parametrize("center", [(40.7308, -73.9973), (42.3601, -71.0589)])  # NYC, Boston
@pytest.mark.parametrize("radius", [500.0, 700.0, 1000.0, 1220.0, 3000.0, 4500.0, 4890.0, 15000.0])
def test_query_bounds_cover_the_radius(center: tuple[float, float], radius: float) -> None:
    # THE retrieval-correctness guarantee: every point within the radius falls
    # inside at least one bound. The radii straddle the precision cliffs where
    # an earlier equator-width table dropped up to ~24% of venues (D-021);
    # points are probed at 99% of the radius on 36 bearings — the worst case.
    lat, lon = center
    bounds = query_bounds(lat, lon, radius)
    assert 1 <= len(bounds) <= 9
    for bearing in range(0, 360, 10):
        p_lat, p_lon = _destination(lat, lon, bearing, radius * 0.99)
        assert haversine_m(lat, lon, p_lat, p_lon) <= radius  # probe really is inside
        point_hash = encode(p_lat, p_lon)
        assert any(lo <= point_hash <= hi for lo, hi in bounds), (
            f"uncovered point at bearing {bearing}, radius {radius}, center {center}"
        )


def test_query_bounds_rejects_uncoverable_radius() -> None:
    with pytest.raises(ValueError):
        query_bounds(40.73, -73.99, 6_000_000.0)


def test_covers_is_exact_haversine() -> None:
    # The post-filter must agree with the scoring distance exactly.
    assert covers(40.7308, -73.9973, 1000.0, 40.7350, -73.9973)  # ~470 m
    assert not covers(40.7308, -73.9973, 1000.0, 40.7450, -73.9973)  # ~1.6 km
    assert haversine_m(40.7308, -73.9973, 40.7350, -73.9973) < 1000.0
