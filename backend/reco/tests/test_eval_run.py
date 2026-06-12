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
from evalharness.simulator import EvalInstance, build_instance, generate_users, generate_world


def _instances(seed: int, users: int, venues: int) -> list[EvalInstance]:
    rng = random.Random(seed)
    world = generate_world(rng, venues)
    user_list = generate_users(rng, users)
    return [build_instance(rng, u, world, 40) for u in user_list]


def test_bracket_orders_random_heuristic_oracle() -> None:
    instances = _instances(seed=1, users=120, venues=150)
    floor = evaluate(_random_ranker(1), instances)["ndcg@5"]
    heuristic = evaluate(_heuristic_ranker(), instances)["ndcg@5"]
    ceiling = evaluate(_oracle_ranker(), instances)["ndcg@5"]
    # D-007/D-020: the heuristic clears noise but cannot reach the oracle, which
    # ranks by the clean true-utility signal it only partially observes.
    assert floor < heuristic < ceiling


def test_oracle_perfectly_orders_true_utility() -> None:
    # The oracle ranks by the same clean utility NDCG grades against, so it is
    # 1.0 BY DEFINITION — an idealized perfect-knowledge ceiling, not an
    # achievable target. Honest only because grading is against clean truth, not
    # the noisy label draw the oracle sorted by (the D-020 fix).
    instances = _instances(seed=7, users=50, venues=120)
    assert evaluate(_oracle_ranker(), instances)["ndcg@5"] > 0.999


def test_heuristic_holds_a_known_baseline_band() -> None:
    # Tighter than "beats random": pins the heuristic to a band around its
    # known-good value, so a gross regression that collapsed it toward random is
    # caught here (partial weight-zeroing is caught by the per-component scorer
    # tests, which the aggregate gate cannot see).
    instances = _instances(seed=1, users=200, venues=200)
    heuristic = evaluate(_heuristic_ranker(), instances)["ndcg@5"]
    assert 0.75 <= heuristic <= 0.90


def test_main_passes_gate_and_exits_zero() -> None:
    # --no-doc so the test never rewrites the committed docs/ALGORITHM.md block.
    assert main(["--no-doc", "--seed", "3", "--users", "100", "--venues", "150"]) == 0
