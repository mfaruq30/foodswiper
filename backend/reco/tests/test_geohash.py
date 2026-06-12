"""Geohash encode + radius query bounds — the Firestore retrieval math."""

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


def test_query_bounds_cover_the_radius() -> None:
    # Every venue within the radius must fall inside at least one bound —
    # this is the guarantee retrieval correctness rests on. Probe a ring of
    # points at 80% of the radius in 8 directions.
    lat, lon, radius = 40.7308, -73.9973, 3000.0
    bounds = query_bounds(lat, lon, radius)
    assert 1 <= len(bounds) <= 9
    deg = radius * 0.8 / 111_320.0  # ~meters per degree latitude
    for dy, dx in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
        point_hash = encode(lat + dy * deg, lon + dx * deg)
        assert any(lo <= point_hash <= hi for lo, hi in bounds), f"uncovered at ({dy},{dx})"


def test_covers_is_exact_haversine() -> None:
    # The post-filter must agree with the scoring distance exactly.
    assert covers(40.7308, -73.9973, 1000.0, 40.7350, -73.9973)  # ~470 m
    assert not covers(40.7308, -73.9973, 1000.0, 40.7450, -73.9973)  # ~1.6 km
    assert haversine_m(40.7308, -73.9973, 40.7350, -73.9973) < 1000.0
