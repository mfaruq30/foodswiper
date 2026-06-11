"""Fuzzy matching: OSM POIs <-> city inspection/license records.

Method (validated against POI-conflation literature): candidate generation by
~111m grid buckets, then name similarity (RapidFuzz token_set_ratio) gated by
geographic distance. Expected auto-match coverage is ~50-75% for NYC — the
binding constraint is dataset overlap, not classifier accuracy, which is why
unmatched POIs still seed (they just miss inspection enrichment).
"""

from collections import defaultdict

from rapidfuzz import fuzz

from .config import MATCH_MAX_DISTANCE_M, MATCH_MIN_NAME_SCORE
from .geo import grid_key, haversine_m, neighbor_keys
from .names import normalize_name
from .records import InspectionRecord, Match, OsmPoi


def match_pois(
    pois: list[OsmPoi], inspections: list[InspectionRecord]
) -> dict[tuple[str, int], tuple[Match, InspectionRecord]]:
    """Return the best inspection match per POI, keyed by (osm_type, osm_id).

    One inspection record may match multiple POIs (food courts share a
    geocode); that is acceptable for enrichment purposes and mirrors reality.
    """
    buckets: dict[tuple[int, int], list[InspectionRecord]] = defaultdict(list)
    for rec in inspections:
        buckets[grid_key(rec.lat, rec.lon)].append(rec)

    norm_cache = {id(rec): normalize_name(rec.name) for rec in inspections}

    out: dict[tuple[str, int], tuple[Match, InspectionRecord]] = {}
    for poi in pois:
        poi_norm = normalize_name(poi.name)
        # Best = highest name score, distance as tiebreak. The tiebreak is
        # load-bearing: token_set_ratio scores "Shake Shack" against every
        # "Shake Shack <branch>" at 100, so proximity must pick the branch.
        best: tuple[float, float, InspectionRecord] | None = None
        for key in neighbor_keys(grid_key(poi.lat, poi.lon)):
            for rec in buckets.get(key, ()):
                distance = haversine_m(poi.lat, poi.lon, rec.lat, rec.lon)
                if distance > MATCH_MAX_DISTANCE_M:
                    continue
                score = fuzz.token_set_ratio(poi_norm, norm_cache[id(rec)])
                if score < MATCH_MIN_NAME_SCORE:
                    continue
                if best is None or (score, -distance) > (best[0], -best[1]):
                    best = (score, distance, rec)
        if best is not None:
            score, _, rec = best
            match = Match(
                osm_type=poi.osm_type,
                osm_id=poi.osm_id,
                inspection_source=rec.source,
                inspection_ref=rec.ref,
                confidence=round(score / 100.0, 4),
            )
            out[(poi.osm_type, poi.osm_id)] = (match, rec)
    return out
