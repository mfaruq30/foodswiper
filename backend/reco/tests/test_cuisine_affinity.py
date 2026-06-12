"""Cuisine adjacency is a hand-built, versioned contract — lock its behavior."""

from app.cuisine_affinity import CANONICAL_CUISINES, affinity, pair_affinity


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
