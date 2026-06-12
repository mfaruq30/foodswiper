"""Consumer-side guard on the canonical venues.ndjson contract (D-019).

The seed side pins what it EMITS (test_canonical.py); this pins what reco
CONSUMES. A key rename in either package now fails loudly in tests instead of
breaking the $0 demo at boot.
"""

import json
from pathlib import Path

from app.adapters.memory import InMemoryVenueRepository, restaurant_from_canonical
from app.models import Mode, OpenState, RequestContext

# One representative line, mirroring seed's to_canonical() key set exactly.
CANONICAL_SAMPLE = {
    "id": "osm:node:42",
    "name": "Test Diner",
    "cuisines": ["diner"],
    "cuisines_raw": ["diner"],
    "price_tier": 2,
    "price_imputed": True,
    "lat": 40.7308,
    "lon": -73.9973,
    "metro": "nyc",
    "hours_raw": "Mo-Su 09:00-22:00",
    "phone": None,
    "website": None,
    "address": "1 Test St",
    "dietary_tags": ["vegetarian"],
    "source": "osm",
    "source_license": "ODbL-1.0",
    "external_ref": {"camis": "40000001"},
    "popularity_prior": 0.75,
}


def test_canonical_record_maps_to_domain() -> None:
    restaurant = restaurant_from_canonical(CANONICAL_SAMPLE)
    assert restaurant.id == "osm:node:42"
    assert restaurant.cuisines == ["diner"]
    assert restaurant.price_tier == 2 and restaurant.price_imputed is True
    assert (restaurant.lat, restaurant.lon) == (40.7308, -73.9973)
    assert restaurant.dietary_tags == ["vegetarian"]
    assert restaurant.popularity_prior == 0.75
    # Hours parsing is Phase 5 — until then everything is honestly UNKNOWN.
    assert restaurant.open_state is OpenState.UNKNOWN


def test_ndjson_load_serves_candidates(tmp_path: Path) -> None:
    path = tmp_path / "venues.ndjson"
    path.write_text(json.dumps(CANONICAL_SAMPLE) + "\n", encoding="utf-8")
    repo = InMemoryVenueRepository.from_ndjson(path)
    ctx = RequestContext(
        mode=Mode.DINE_IN, metro="nyc", user_lat=40.7308, user_lon=-73.9973, max_distance_m=1000
    )
    assert [r.id for r in repo.find_candidates(ctx)] == ["osm:node:42"]
    assert repo.get_by_ids(["osm:node:42"])[0].name == "Test Diner"
