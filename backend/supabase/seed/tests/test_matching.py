"""OSM <-> inspection matching behavior."""

from munch_seed.matching import match_pois
from munch_seed.records import InspectionRecord, OsmPoi


def _poi(name: str, lat: float, lon: float) -> OsmPoi:
    return OsmPoi(
        osm_type="node",
        osm_id=hash(name) % 10**9,
        name=name,
        lat=lat,
        lon=lon,
        category="restaurant",
    )


def _rec(ref: str, name: str, lat: float, lon: float) -> InspectionRecord:
    return InspectionRecord(source="nyc_open_data", ref=ref, name=name, lat=lat, lon=lon)


def test_same_name_nearby_matches() -> None:
    poi = _poi("Joe's Pizza", 40.7305, -74.0021)
    rec = _rec("41000001", "JOE'S PIZZA", 40.7306, -74.0022)  # ~14m away
    matches = match_pois([poi], [rec])
    match, matched_rec = matches[("node", poi.osm_id)]
    assert matched_rec.ref == "41000001"
    assert match.confidence >= 0.85


def test_same_name_far_away_does_not_match() -> None:
    poi = _poi("Joe's Pizza", 40.7305, -74.0021)
    rec = _rec("41000002", "Joe's Pizza", 40.7400, -74.0021)  # ~1km north
    assert match_pois([poi], [rec]) == {}


def test_different_name_nearby_does_not_match() -> None:
    poi = _poi("Sushi Yasuda", 40.7305, -74.0021)
    rec = _rec("41000003", "Patsy's Tavern", 40.7306, -74.0022)
    assert match_pois([poi], [rec]) == {}


def test_equal_name_scores_break_by_distance() -> None:
    # token_set_ratio scores both candidates 100 ("Shake Shack" is a token
    # subset of "Shake Shack Madison Sq"), so the closer record must win.
    poi = _poi("Shake Shack", 40.7415, -73.9883)
    closer = _rec("A", "SHAKE SHACK", 40.7416, -73.9884)  # ~14m
    farther = _rec("B", "Shake Shack Madison Sq", 40.7410, -73.9876)  # ~80m
    matches = match_pois([poi], [farther, closer])
    _, matched_rec = matches[("node", poi.osm_id)]
    assert matched_rec.ref == "A"
