"""Ranking metrics (spec §7.4). Pure functions over a ranked id list.

Binary-relevance metrics take the set of relevant ids; NDCG takes graded
relevance (the simulator's latent utility) so it rewards putting the *most*
relevant items highest, not merely relevant-vs-not.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence


def precision_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    """Fraction of the top-k that are relevant."""
    if k <= 0:
        return 0.0
    top = ranked[:k]
    hits = sum(1 for item in top if item in relevant)
    return hits / k


def recall_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    """Fraction of all relevant items captured in the top-k."""
    if not relevant:
        return 0.0
    hits = sum(1 for item in ranked[:k] if item in relevant)
    return hits / len(relevant)


def hit_rate_at_k(ranked: Sequence[str], relevant: set[str], k: int) -> float:
    """1.0 if any relevant item appears in the top-k, else 0.0.

    The metric that most directly models the product: a swipe deck succeeds if
    a good match shows up early, even if the rest is noise.
    """
    return 1.0 if any(item in relevant for item in ranked[:k]) else 0.0


def mrr(ranked: Sequence[str], relevant: set[str]) -> float:
    """Reciprocal rank of the first relevant item (0 if none)."""
    for index, item in enumerate(ranked, start=1):
        if item in relevant:
            return 1.0 / index
    return 0.0


def ndcg_at_k(ranked: Sequence[str], relevance: Mapping[str, float], k: int) -> float:
    """Normalized discounted cumulative gain at k, with graded relevance.

    DCG discounts each item's gain by log2(position + 1); IDCG is the DCG of
    the perfect ordering, so NDCG is in [0, 1] and comparable across queries
    whose relevance mass differs.
    """
    if k <= 0:
        return 0.0
    dcg = 0.0
    for index, item in enumerate(ranked[:k], start=1):
        dcg += relevance.get(item, 0.0) / math.log2(index + 1)
    ideal_gains = sorted(relevance.values(), reverse=True)[:k]
    idcg = sum(gain / math.log2(index + 1) for index, gain in enumerate(ideal_gains, start=1))
    if idcg == 0.0:
        return 0.0
    return dcg / idcg
