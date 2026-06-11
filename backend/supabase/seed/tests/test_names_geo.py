"""Name normalization + geographic helpers."""

from munch_seed.geo import grid_key, haversine_m, neighbor_keys
from munch_seed.names import normalize_name


def test_noise_tokens_drop() -> None:
    assert normalize_name("Joe's Pizza Restaurant") == "joe s pizza"
    assert normalize_name("The Halal Guys NYC") == "halal guys"


def test_all_noise_falls_back_to_raw_tokens() -> None:
    # "The Restaurant" must not normalize to "" — empty keys collide.
    assert normalize_name("The Restaurant") == "the restaurant"


def test_haversine_known_distance() -> None:
    # Empire State Building -> Grand Central: ~0.86 km great-circle.
    d = haversine_m(40.7484, -73.9857, 40.7527, -73.9772)
    assert 820 < d < 900


def test_haversine_zero() -> None:
    assert haversine_m(42.36, -71.06, 42.36, -71.06) == 0.0


def test_grid_neighbors_cover_adjacent_cells() -> None:
    key = grid_key(40.7484, -73.9857)
    neighbors = neighbor_keys(key)
    assert key in neighbors
    assert len(neighbors) == 9
    # A point ~100m north lands in an adjacent cell that the 3x3 covers.
    north = grid_key(40.7484 + 0.001, -73.9857)
    assert north in neighbors
