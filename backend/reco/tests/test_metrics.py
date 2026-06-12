"""Ranking metrics, checked against hand-computed small examples."""

import math

from evalharness.metrics import (
    hit_rate_at_k,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def test_precision_and_recall() -> None:
    ranked = ["a", "b", "c", "d"]
    relevant = {"a", "c"}
    assert precision_at_k(ranked, relevant, 2) == 0.5  # a relevant, b not
    assert recall_at_k(ranked, relevant, 2) == 0.5  # captured a of {a, c}
    assert recall_at_k(ranked, relevant, 4) == 1.0


def test_hit_rate_and_mrr() -> None:
    assert hit_rate_at_k(["x", "a"], {"a"}, 1) == 0.0  # a not in top 1
    assert hit_rate_at_k(["x", "a"], {"a"}, 2) == 1.0
    assert mrr(["x", "a", "b"], {"a"}) == 0.5  # first relevant at rank 2
    assert mrr(["x", "y"], {"a"}) == 0.0  # none relevant


def test_ndcg_perfect_and_reversed() -> None:
    relevance = {"a": 3.0, "b": 2.0, "c": 1.0}
    assert ndcg_at_k(["a", "b", "c"], relevance, 3) == 1.0
    reversed_ndcg = ndcg_at_k(["c", "b", "a"], relevance, 3)
    assert reversed_ndcg < 1.0

    # Spot-check the discount math on a single swap.
    swapped = ndcg_at_k(["b", "a", "c"], relevance, 3)
    dcg = 2.0 / math.log2(2) + 3.0 / math.log2(3) + 1.0 / math.log2(4)
    idcg = 3.0 / math.log2(2) + 2.0 / math.log2(3) + 1.0 / math.log2(4)
    assert abs(swapped - dcg / idcg) < 1e-9


def test_empty_relevance_is_zero_not_error() -> None:
    assert ndcg_at_k(["a"], {}, 5) == 0.0
    assert recall_at_k(["a"], set(), 5) == 0.0
