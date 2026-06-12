"""The eval harness must satisfy its own gate: random < heuristic < oracle.

This is the test that proves the heart of the product works end to end — the
scorer, the metrics, and the honesty bracket — on a small reproducible run.
"""

import random

from evalharness.run import (
    _heuristic_ranker,
    _oracle_ranker,
    _random_ranker,
    evaluate,
    main,
)
from evalharness.simulator import build_instance, generate_users, generate_world


def _instances(seed: int, users: int, venues: int) -> list:  # type: ignore[type-arg]
    rng = random.Random(seed)
    world = generate_world(rng, venues)
    user_list = generate_users(rng, users)
    return [build_instance(rng, u, world, 40) for u in user_list]


def test_bracket_orders_random_heuristic_oracle() -> None:
    instances = _instances(seed=1, users=120, venues=150)
    floor = evaluate(_random_ranker(1), instances)["ndcg@5"]
    heuristic = evaluate(_heuristic_ranker(), instances)["ndcg@5"]
    ceiling = evaluate(_oracle_ranker(), instances)["ndcg@5"]
    # The whole point of D-007: the heuristic beats noise but cannot reach the
    # oracle, because the simulator hides the `vibe` signal from it.
    assert floor < heuristic < ceiling


def test_oracle_is_perfect_on_its_own_ground_truth() -> None:
    # The oracle ranks by true utility, so its NDCG (graded by that same
    # utility) must be 1.0 — a sanity check that the metric and oracle agree.
    instances = _instances(seed=7, users=50, venues=120)
    assert evaluate(_oracle_ranker(), instances)["ndcg@5"] > 0.999


def test_main_passes_gate_and_exits_zero() -> None:
    assert main(["--seed", "3", "--users", "100", "--venues", "150"]) == 0
