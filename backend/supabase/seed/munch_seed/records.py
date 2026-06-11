"""Shared dataclasses passed between pipeline stages.

Kept dependency-free so every stage (and every test) can import them without
pulling in osmium/httpx/psycopg.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class OsmPoi:
    """A restaurant-like POI extracted from an OSM PBF file."""

    osm_type: str  # 'node' | 'way'
    osm_id: int
    name: str
    lat: float
    lon: float
    category: str  # raw amenity value: restaurant | fast_food | cafe
    cuisines_raw: list[str] = field(default_factory=list)
    opening_hours: str | None = None
    phone: str | None = None
    website: str | None = None
    address: str | None = None
    dietary_tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class InspectionRecord:
    """One establishment from a city inspection / license dataset."""

    source: str  # 'nyc_open_data' | 'boston_open_data'
    ref: str  # CAMIS (NYC) or license number (Boston)
    name: str
    lat: float
    lon: float
    cuisine_description: str | None = None
    last_seen: str | None = None  # ISO date of latest inspection / license issue


@dataclass(slots=True)
class Match:
    """A persisted OSM <-> inspection match decision (-> source_matches)."""

    osm_type: str
    osm_id: int
    inspection_source: str
    inspection_ref: str
    confidence: float


@dataclass(slots=True)
class Venue:
    """A curated row ready to upsert into public.restaurants."""

    osm_type: str
    osm_id: int
    name: str
    cuisines: list[str]
    cuisines_raw: list[str]
    price_tier: int
    lat: float
    lon: float
    metro: str
    hours_raw: str | None
    phone: str | None
    website: str | None
    address: str | None
    dietary_tags: list[str]
    source_license: str
    external_ref: dict[str, str]
    popularity_prior: float
