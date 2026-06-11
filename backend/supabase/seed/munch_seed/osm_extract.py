"""OSM PBF extraction: restaurant-like POIs within a metro bounding box.

Memory strategy (why two passes): a full node-location index for the New York
extract would cost gigabytes. Instead, pass 1 streams ways and remembers only
the node refs of *candidate* ways (a few thousand); pass 2 streams nodes,
emitting candidate node-POIs directly and capturing locations only for the
refs pass 1 asked for. Way centroids are then computed from those locations.
Relations are skipped in v1: restaurant relations are rare (<1%) and the
assembly cost is not worth it for a curated 800/metro seed.

Tag handling: osmium TagLists are only valid inside their callback, so
candidates are snapshotted to plain dicts immediately; all helpers therefore
type against Mapping[str, str].
"""

from collections.abc import Mapping

import osmium

from .config import AMENITY_VALUES, MetroBounds
from .records import OsmPoi

# OSM tags that mark a venue as permanently gone — never seed these.
_CLOSED_MARKERS = ("disused:amenity", "abandoned:amenity", "was:amenity")

# diet:<key>=yes|only -> Munch dietary tag.
_DIET_KEYS = ("vegetarian", "vegan", "halal", "kosher", "gluten_free")

# _wanted gates BEFORE the dict snapshot (TagLists die with their callback,
# and snapshotting every element in a 470 MB extract would be pure waste), so
# it accepts either the live TagList or an already-snapshotted dict.
_TagsLike = osmium.osm.TagList | Mapping[str, str]


def _wanted(tags: _TagsLike) -> bool:
    """A candidate is an open, named restaurant/fast_food/cafe."""
    if tags.get("amenity") not in AMENITY_VALUES or "name" not in tags:
        return False
    return all(marker not in tags for marker in _CLOSED_MARKERS)


def _dietary_tags(tags: Mapping[str, str]) -> list[str]:
    return [key for key in _DIET_KEYS if tags.get(f"diet:{key}") in ("yes", "only")]


def _address(tags: Mapping[str, str]) -> str | None:
    number = tags.get("addr:housenumber")
    street = tags.get("addr:street")
    if not street:
        return None
    return f"{number} {street}" if number else street


def _poi_from_tags(
    osm_type: str, osm_id: int, lat: float, lon: float, tags: Mapping[str, str]
) -> OsmPoi:
    return OsmPoi(
        osm_type=osm_type,
        osm_id=osm_id,
        name=tags["name"],
        lat=lat,
        lon=lon,
        category=tags["amenity"],
        cuisines_raw=[p.strip() for p in tags.get("cuisine", "").split(";") if p.strip()],
        opening_hours=tags.get("opening_hours"),
        phone=tags.get("phone") or tags.get("contact:phone"),
        website=tags.get("website") or tags.get("contact:website"),
        address=_address(tags),
        dietary_tags=_dietary_tags(tags),
    )


class _WayScan(osmium.SimpleHandler):
    """Pass 1: remember candidate ways and which node locations they need."""

    def __init__(self) -> None:
        super().__init__()
        # way id -> (tag snapshot, ordered node refs)
        self.candidates: dict[int, tuple[dict[str, str], list[int]]] = {}
        self.needed_refs: set[int] = set()

    def way(self, w: "osmium.osm.Way") -> None:
        # TagList supports .get/in, so _wanted can gate cheaply before the
        # dict snapshot — only candidates pay the copy.
        if not _wanted(w.tags):
            return
        refs = [n.ref for n in w.nodes]
        if not refs:
            return
        self.candidates[w.id] = ({t.k: t.v for t in w.tags}, refs)
        self.needed_refs.update(refs)


class _NodeScan(osmium.SimpleHandler):
    """Pass 2: emit node POIs in-bbox; capture locations pass 1 asked for."""

    def __init__(self, bounds: MetroBounds, needed_refs: set[int]) -> None:
        super().__init__()
        self._bounds = bounds
        self._needed = needed_refs
        self.node_pois: list[OsmPoi] = []
        self.locations: dict[int, tuple[float, float]] = {}

    def node(self, n: "osmium.osm.Node") -> None:
        lon, lat = n.location.lon, n.location.lat
        if n.id in self._needed:
            self.locations[n.id] = (lat, lon)
        if _wanted(n.tags) and self._bounds.contains(lon, lat):
            tags = {t.k: t.v for t in n.tags}
            self.node_pois.append(_poi_from_tags("node", n.id, lat, lon, tags))


def extract_pois(pbf_path: str, bounds: MetroBounds) -> list[OsmPoi]:
    """Stream a Geofabrik PBF twice and return in-bbox restaurant POIs."""
    way_scan = _WayScan()
    way_scan.apply_file(pbf_path)

    node_scan = _NodeScan(bounds, way_scan.needed_refs)
    node_scan.apply_file(pbf_path)

    pois = list(node_scan.node_pois)
    for way_id, (tags, refs) in way_scan.candidates.items():
        located = [node_scan.locations[r] for r in refs if r in node_scan.locations]
        if not located:
            continue  # way entirely outside the extract's node set
        lat = sum(point[0] for point in located) / len(located)
        lon = sum(point[1] for point in located) / len(located)
        if bounds.contains(lon, lat):
            pois.append(_poi_from_tags("way", way_id, lat, lon, tags))
    return pois
