"""Pipeline configuration: metro boundaries, sources, curation knobs.

Everything tunable lives here, never inline in stage code (spec §7.2 spirit).
"""

from dataclasses import dataclass

# Geofabrik daily extracts (D-005). Downloaded once per run, cached locally.
GEOFABRIK_URLS = {
    "nyc": "https://download.geofabrik.de/north-america/us/new-york-latest.osm.pbf",
    "boston": "https://download.geofabrik.de/north-america/us/massachusetts-latest.osm.pbf",
}

# NYC DOHMH inspections (Socrata). Open terms; row-level license recorded below.
NYC_SOCRATA_URL = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"

# Analyze Boston: the ACTIVE licenses dataset, not the legacy violation-level
# inspections table (no cuisine field, text coords, 2006-era rows) — D-011.
BOSTON_CKAN_API = "https://data.boston.gov/api/3/action"
BOSTON_LICENSES_DATASET = "active-food-establishment-licenses"

# Per-row license identifiers (spec §6.4: record source + license per row).
LICENSE_OSM = "ODbL-1.0"
LICENSE_NYC = "NYC-Open-Data-Terms"
LICENSE_BOSTON = "PDDL-1.0"


@dataclass(frozen=True, slots=True)
class MetroBounds:
    """Inclusive WGS84 bounding box used by the OSM extraction pass."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def contains(self, lon: float, lat: float) -> bool:
        return self.min_lon <= lon <= self.max_lon and self.min_lat <= lat <= self.max_lat


# D-011: "Boston" includes Cambridge / Somerville / Brookline / Allston —
# where students actually eat. Inspection enrichment only covers Boston city
# (Analyze Boston's scope); the rest are OSM-only and that is accepted.
METRO_BOUNDS: dict[str, MetroBounds] = {
    "nyc": MetroBounds(min_lon=-74.27, min_lat=40.48, max_lon=-73.68, max_lat=40.93),
    "boston": MetroBounds(min_lon=-71.20, min_lat=42.26, max_lon=-70.98, max_lat=42.43),
}

# OSM amenity values that count as "restaurant-like" for Munch v1.
AMENITY_VALUES = frozenset({"restaurant", "fast_food", "cafe"})

# Curation target per metro (spec §6.4: ~500-1000).
TARGET_PER_METRO = 800

# Near-duplicate suppression: same normalized name within this distance is
# one venue (chains keep distinct branches because they sit farther apart).
DEDUPE_RADIUS_M = 75.0

# Matching thresholds (validated against POI-conflation literature: name
# similarity + geo distance, ~90% pairwise precision at these levels).
MATCH_MAX_DISTANCE_M = 120.0
MATCH_MIN_NAME_SCORE = 85.0

# v1 price imputation (D-010): category baseline, cuisine bumps. Every seeded
# row carries price_imputed=true; a manual labeling pass refines later.
PRICE_BY_CATEGORY = {"fast_food": 1, "cafe": 2, "restaurant": 2}
PRICE_TIER_3_CUISINES = frozenset(
    {"steakhouse", "sushi", "french", "seafood", "korean_bbq", "omakase"}
)
