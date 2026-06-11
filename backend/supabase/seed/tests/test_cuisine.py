"""Cuisine canonicalization is a persisted contract — lock its behavior."""

from munch_seed.cuisine import canonicalize_dohmh, canonicalize_osm


def test_multi_value_tags_split_and_dedupe() -> None:
    assert canonicalize_osm("burger;american;diner") == ["burger", "american", "diner"]
    # 'ice_cream' and 'donut' both canonicalize to dessert — no duplicates.
    assert canonicalize_osm("ice_cream;donut") == ["dessert"]


def test_aliases_map_to_canonical_nodes() -> None:
    assert canonicalize_osm("sichuan") == ["chinese"]
    assert canonicalize_osm("steak_house") == ["steakhouse"]
    assert canonicalize_osm("coffee_shop") == ["coffee"]


def test_unknown_tags_drop_rather_than_guess() -> None:
    assert canonicalize_osm("klingon") == []
    assert canonicalize_osm(None) == []
    assert canonicalize_osm("") == []


def test_spaces_normalize_to_underscores() -> None:
    assert canonicalize_osm("bubble tea") == ["bubble_tea"]


def test_dohmh_descriptions() -> None:
    assert canonicalize_dohmh("Jewish/Kosher") == ["kosher"]
    assert canonicalize_dohmh("CHINESE") == ["chinese"]
    assert canonicalize_dohmh("Pancakes/Waffles") == ["breakfast"]
    assert canonicalize_dohmh("Not A Real Cuisine") == []
    assert canonicalize_dohmh(None) == []
