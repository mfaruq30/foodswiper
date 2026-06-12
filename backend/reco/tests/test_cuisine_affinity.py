"""Cuisine adjacency is a hand-built, versioned contract — lock its behavior."""

from app.cuisine_affinity import _EDGES, CANONICAL_CUISINES, affinity, pair_affinity


def test_self_affinity_is_one() -> None:
    assert pair_affinity("italian", "italian") == 1.0


def test_near_and_unrelated_pairs() -> None:
    assert pair_affinity("japanese", "sushi") == 0.6
    assert pair_affinity("mexican", "latin") == 0.6
    assert pair_affinity("sushi", "bbq") == 0.0


def test_symmetry() -> None:
    for a, b in [("thai", "vietnamese"), ("italian", "pizza"), ("bbq", "southern")]:
        assert pair_affinity(a, b) == pair_affinity(b, a)


def test_affinity_takes_best_matching_pair() -> None:
    # User loves Italian; a pizza place should score via the italian-pizza edge,
    # not be diluted by also carrying an unrelated tag.
    weights = {"italian": 1.0}
    assert affinity(weights, ["pizza", "bbq"]) == 0.6
    # Exact-match cuisine beats a neighbor.
    assert affinity(weights, ["italian"]) == 1.0


def test_affinity_scales_with_user_weight() -> None:
    assert affinity({"italian": 0.5}, ["pizza"]) == 0.3
    assert affinity({}, ["pizza"]) == 0.0


def test_canonical_vocabulary_is_populated() -> None:
    assert "italian" in CANONICAL_CUISINES
    assert "sushi" in CANONICAL_CUISINES
    assert len(CANONICAL_CUISINES) >= 40


def test_affinity_clamps_malformed_weights() -> None:
    # A weight > 1 (a data error) must not push the term past 1.0.
    assert affinity({"italian": 2.0}, ["italian"]) == 1.0


def test_edge_map_has_no_self_loops_or_duplicates() -> None:
    # Copy-paste guard for the hand-maintained map (D-009): a self-loop or a
    # duplicated undirected pair is a human error worth failing on, not silently
    # absorbing via the dedup-by-max in _build_lookup.
    seen: set[frozenset[str]] = set()
    for a, b, _weight in _EDGES:
        assert a != b, f"self-loop on {a}"
        pair = frozenset({a, b})
        assert pair not in seen, f"duplicate edge {a}-{b}"
        seen.add(pair)
