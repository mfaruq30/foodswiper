"""Curation: turn raw POIs + matches into the seedable venue set.

Selection policy (config-tunable, documented for the gate):
  must-have: name, location, >=1 canonical cuisine (backfilled from DOHMH for
             matched NYC venues missing OSM cuisine tags);
  ranking:   inspection-matched first, then popularity prior (tag richness +
             inspection recency);
  dedupe:    same normalized name within DEDUPE_RADIUS_M collapses to the
             richest record (chain branches survive — they sit farther apart).
"""

from datetime import UTC, datetime

from .config import (
    DEDUPE_RADIUS_M,
    LICENSE_BOSTON,
    LICENSE_NYC,
    LICENSE_OSM,
    PRICE_BY_CATEGORY,
    PRICE_TIER_3_CUISINES,
    TARGET_PER_METRO,
)
from .cuisine import canonicalize_dohmh, canonicalize_osm
from .geo import grid_key, haversine_m, neighbor_keys
from .names import normalize_name
from .records import InspectionRecord, Match, OsmPoi, Venue


def popularity_prior(poi: OsmPoi, matched: InspectionRecord | None, now: datetime) -> float:
    """Cold-start quality prior in [0, 1] from open data only (spec §7.3).

    Half the weight is "the data is rich" (mappers bother tagging places that
    matter); half is "the city recently confirmed it operates".
    """
    richness = (
        0.15 * bool(poi.website)
        + 0.10 * bool(poi.phone)
        + 0.15 * bool(poi.opening_hours)
        + 0.10 * bool(poi.cuisines_raw)
    )
    recency = 0.0
    if matched is not None:
        recency = 0.25  # exists in a city dataset at all
        if matched.last_seen:
            try:
                seen = datetime.fromisoformat(matched.last_seen.replace("Z", "+00:00"))
                if seen.tzinfo is None:
                    seen = seen.replace(tzinfo=UTC)
                if (now - seen).days <= 365:
                    recency = 0.50  # confirmed operating within the year
            except ValueError:
                pass  # unparseable date keeps the baseline 0.25
    return round(richness + recency, 4)


def _price_tier(category: str, cuisines: list[str]) -> int:
    base = PRICE_BY_CATEGORY.get(category, 2)
    if any(c in PRICE_TIER_3_CUISINES for c in cuisines):
        return max(base, 3)
    return base


def _venue(
    poi: OsmPoi,
    metro: str,
    cuisines: list[str],
    matched: InspectionRecord | None,
    prior: float,
) -> Venue:
    license_parts = [LICENSE_OSM]
    external_ref: dict[str, str] = {}
    if matched is not None:
        if matched.source == "nyc_open_data":
            license_parts.append(LICENSE_NYC)
            external_ref["camis"] = matched.ref
        else:
            license_parts.append(LICENSE_BOSTON)
            external_ref["boston_license"] = matched.ref
    return Venue(
        osm_type=poi.osm_type,
        osm_id=poi.osm_id,
        name=poi.name,
        cuisines=cuisines,
        cuisines_raw=poi.cuisines_raw,
        price_tier=_price_tier(poi.category, cuisines),
        lat=poi.lat,
        lon=poi.lon,
        metro=metro,
        hours_raw=poi.opening_hours,
        phone=poi.phone,
        website=poi.website,
        address=poi.address,
        dietary_tags=poi.dietary_tags,
        source_license="+".join(license_parts),
        external_ref=external_ref,
        popularity_prior=prior,
    )


def curate(
    pois: list[OsmPoi],
    matches: dict[tuple[str, int], tuple[Match, InspectionRecord]],
    metro: str,
    now: datetime,
    target: int = TARGET_PER_METRO,
) -> list[Venue]:
    """Select the top `target` venues for a metro."""
    candidates: list[Venue] = []
    for poi in pois:
        matched = matches.get((poi.osm_type, poi.osm_id))
        inspection = matched[1] if matched else None

        cuisines = canonicalize_osm(";".join(poi.cuisines_raw)) if poi.cuisines_raw else []
        if not cuisines and inspection is not None:
            cuisines = canonicalize_dohmh(inspection.cuisine_description)
        if not cuisines:
            continue  # cuisine is a product must-have (cards, affinity, filters)

        prior = popularity_prior(poi, inspection, now)
        candidates.append(_venue(poi, metro, cuisines, inspection, prior))

    # Matched-first then prior: city confirmation beats tag richness alone.
    candidates.sort(key=lambda v: (bool(v.external_ref), v.popularity_prior), reverse=True)

    # Greedy near-duplicate suppression in rank order, so the richest record
    # of any duplicate cluster is the one that survives.
    kept: list[Venue] = []
    seen_grid: dict[tuple[int, int], list[Venue]] = {}
    for venue in candidates:
        key = grid_key(venue.lat, venue.lon)
        name_norm = normalize_name(venue.name)
        duplicate = any(
            normalize_name(other.name) == name_norm
            and haversine_m(venue.lat, venue.lon, other.lat, other.lon) <= DEDUPE_RADIUS_M
            for nk in neighbor_keys(key)
            for other in seen_grid.get(nk, ())
        )
        if duplicate:
            continue
        kept.append(venue)
        seen_grid.setdefault(key, []).append(venue)
        if len(kept) >= target:
            break
    return kept
