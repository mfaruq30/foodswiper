"""Canonical venue artifact: venues.ndjson — the backend-neutral contract.

Every persistence writer (Firestore now, Postgres again later — D-019)
consumes THIS file, never pipeline internals. Coordinates stay plain WGS84
lat/lon floats so the record maps to a PostGIS geography(Point) or a Firestore
geohash equally trivially; nothing backend-specific is ever emitted here.

The stable venue id is "osm:<type>:<id>" — derived from the upsert identity
(osm_type, osm_id) so re-seeds and backend migrations preserve identity, and
swipe history can always be re-linked to the same venue.
"""

import json
from collections.abc import Iterable
from pathlib import Path

from .records import Venue


def venue_id(venue: Venue) -> str:
    return f"osm:{venue.osm_type}:{venue.osm_id}"


def to_canonical(venue: Venue) -> dict[str, object]:
    """One ndjson record. Keys are the cross-backend schema — change with care
    (both the reco memory adapter and the Firestore writer read these)."""
    return {
        "id": venue_id(venue),
        "name": venue.name,
        "cuisines": venue.cuisines,
        "cuisines_raw": venue.cuisines_raw,
        "price_tier": venue.price_tier,
        "price_imputed": True,  # all v1 prices are imputed (D-010)
        "lat": round(venue.lat, 7),
        "lon": round(venue.lon, 7),
        "metro": venue.metro,
        "hours_raw": venue.hours_raw,
        "phone": venue.phone,
        "website": venue.website,
        "address": venue.address,
        "dietary_tags": venue.dietary_tags,
        "source": "osm",
        "source_license": venue.source_license,
        "external_ref": venue.external_ref,
        "popularity_prior": venue.popularity_prior,
    }


def write_ndjson(venues: Iterable[Venue], path: Path) -> int:
    """Write (or overwrite) the canonical artifact; returns the record count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for venue in venues:
            fh.write(json.dumps(to_canonical(venue), ensure_ascii=False) + "\n")
            count += 1
    return count


def append_ndjson(venues: Iterable[Venue], path: Path) -> int:
    """Append a metro's venues (the pipeline runs one metro at a time)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        for venue in venues:
            fh.write(json.dumps(to_canonical(venue), ensure_ascii=False) + "\n")
            count += 1
    return count
