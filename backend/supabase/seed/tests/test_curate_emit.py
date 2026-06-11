"""Curation policy + SQL emission safety."""

from datetime import UTC, datetime

from munch_seed.curate import curate, popularity_prior
from munch_seed.emit import tombstone_sql, venue_upsert_sql, write_sql_chunks
from munch_seed.matching import match_pois
from munch_seed.records import InspectionRecord, OsmPoi

NOW = datetime(2026, 6, 11, tzinfo=UTC)


def _poi(
    osm_id: int,
    name: str,
    lat: float = 40.73,
    lon: float = -74.0,
    cuisines: list[str] | None = None,
    **extra: str,
) -> OsmPoi:
    return OsmPoi(
        osm_type="node",
        osm_id=osm_id,
        name=name,
        lat=lat,
        lon=lon,
        category="restaurant",
        cuisines_raw=cuisines if cuisines is not None else ["italian"],
        opening_hours=extra.get("opening_hours"),
        website=extra.get("website"),
    )


def test_cuisineless_unmatched_poi_is_excluded() -> None:
    venues = curate([_poi(1, "Mystery Spot", cuisines=[])], {}, "nyc", NOW)
    assert venues == []


def test_cuisineless_matched_poi_backfills_from_dohmh() -> None:
    poi = _poi(2, "Lucali", cuisines=[])
    rec = InspectionRecord(
        source="nyc_open_data",
        ref="40000001",
        name="LUCALI",
        lat=poi.lat + 0.0001,
        lon=poi.lon,
        cuisine_description="Pizza",
    )
    matches = match_pois([poi], [rec])
    venues = curate([poi], matches, "nyc", NOW)
    assert len(venues) == 1
    assert venues[0].cuisines == ["pizza"]
    assert venues[0].external_ref == {"camis": "40000001"}
    assert "NYC-Open-Data-Terms" in venues[0].source_license


def test_near_duplicates_collapse_keeping_richest() -> None:
    rich = _poi(3, "Via Carota", website="https://viacarota.com", opening_hours="Mo-Su 11:00-23:00")
    poor = _poi(4, "Via Carota", lat=40.7301, lon=-74.0001)  # ~15m away
    venues = curate([poor, rich], {}, "nyc", NOW)
    assert len(venues) == 1
    assert venues[0].osm_id == 3  # higher prior survives


def test_chain_branches_far_apart_both_survive() -> None:
    a = _poi(5, "Shake Shack", lat=40.7415, lon=-73.9883)
    b = _poi(6, "Shake Shack", lat=40.7791, lon=-73.9550)  # ~5km away
    venues = curate([a, b], {}, "nyc", NOW)
    assert len(venues) == 2


def test_popularity_prior_rewards_recent_inspection() -> None:
    poi = _poi(7, "Test")
    recent = InspectionRecord(
        source="nyc_open_data",
        ref="X",
        name="TEST",
        lat=0,
        lon=0,
        last_seen="2026-05-01T00:00:00.000",
    )
    stale = InspectionRecord(
        source="nyc_open_data",
        ref="Y",
        name="TEST",
        lat=0,
        lon=0,
        last_seen="2022-01-01T00:00:00.000",
    )
    assert popularity_prior(poi, recent, NOW) > popularity_prior(poi, stale, NOW)
    assert popularity_prior(poi, stale, NOW) > popularity_prior(poi, None, NOW)


def test_sql_quotes_names_safely() -> None:
    venues = curate([_poi(8, "Mama's; drop table -- 'pizza'")], {}, "nyc", NOW)
    sql = venue_upsert_sql(venues)
    assert "Mama''s; drop table -- ''pizza''" in sql
    assert "on conflict (osm_type, osm_id) do update" in sql


def test_tombstone_never_touches_user_rows() -> None:
    sql = tombstone_sql("nyc", "2026-06-11T00:00:00+00:00")
    assert "source <> 'user'" in sql
    assert "is_active = false" in sql
    assert "delete" not in sql.lower()


def test_write_sql_chunks_orders_files(tmp_path: object) -> None:
    from pathlib import Path

    out = Path(str(tmp_path))
    venues = curate([_poi(9, "A"), _poi(10, "B", lat=40.8)], {}, "nyc", NOW)
    paths = write_sql_chunks(venues, [], "nyc", "2026-06-11T00:00:00+00:00", out, chunk_size=1)
    names = [p.name for p in paths]
    # Venue chunks, then scores init, then tombstone — order is load-bearing.
    assert names == sorted(names)
    assert names[-1].endswith("40_tombstone.sql")
