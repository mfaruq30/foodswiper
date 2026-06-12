"""The canonical ndjson artifact is a cross-backend contract — lock it."""

import json
from datetime import UTC, datetime
from pathlib import Path

from munch_seed.canonical import to_canonical, venue_id, write_ndjson
from munch_seed.curate import curate
from munch_seed.geohash import encode
from munch_seed.records import OsmPoi, Venue


def _venue() -> Venue:
    poi = OsmPoi(
        osm_type="node",
        osm_id=42,
        name="Test Diner",
        lat=40.7308,
        lon=-73.9973,
        category="restaurant",
        cuisines_raw=["diner"],
    )
    return curate([poi], {}, "nyc", datetime(2026, 6, 12, tzinfo=UTC))[0]


def test_venue_id_is_stable_across_backends() -> None:
    # The id derives from the OSM upsert identity, so re-seeds and backend
    # migrations preserve venue identity (and swipe-history linkage).
    assert venue_id(_venue()) == "osm:node:42"


def test_canonical_record_is_backend_neutral() -> None:
    record = to_canonical(_venue())
    # Plain WGS84 floats — Postgres- and Firestore-portable alike (D-019).
    assert isinstance(record["lat"], float) and isinstance(record["lon"], float)
    # Nothing backend-derived leaks in; geohash/name_lower are writer-added.
    assert "geohash" not in record and "name_lower" not in record
    assert record["source_license"] == "ODbL-1.0"


def test_ndjson_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "venues.ndjson"
    assert write_ndjson([_venue()], path) == 1
    parsed = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert parsed[0]["id"] == "osm:node:42"
    assert parsed[0]["metro"] == "nyc"


def test_geohash_encode_matches_reference() -> None:
    # Same reference point and pinned value as the reco-side test
    # (test_geohash.py): the two encoder copies MUST agree or range queries
    # miss seeded venues.
    assert encode(40.7308, -73.9973, 7) == "dr5rsnu"
    assert len(encode(40.7308, -73.9973)) == 9
