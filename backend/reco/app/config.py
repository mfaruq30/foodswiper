"""Tunable ranking configuration.

Every weight and threshold lives here, never inline in scoring code (spec
§7.2). `CONFIG_VERSION` is logged with each served deck so a ranking change
is always traceable to the config that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass

CONFIG_VERSION = "heuristic-v1"


@dataclass(frozen=True, slots=True)
class ScoringWeights:
    """Layer-2 heuristic weights (spec §7.3). Must sum to 1.0."""

    cuisine_affinity: float = 0.40
    swipe_pattern_match: float = 0.25
    price_fit: float = 0.15
    proximity: float = 0.10
    quality_prior: float = 0.10

    def validate(self) -> None:
        total = (
            self.cuisine_affinity
            + self.swipe_pattern_match
            + self.price_fit
            + self.proximity
            + self.quality_prior
        )
        # Floating tolerance: weights are human-edited and must stay a convex
        # combination, or scores drift out of [0, 1] and break comparability.
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"ScoringWeights must sum to 1.0, got {total}")


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    """All ranking knobs in one versioned object."""

    weights: ScoringWeights = ScoringWeights()

    # Penalty multiplier applied to a candidate whose hours are UNKNOWN, so
    # known-open venues outrank unknowns without the unknowns being dropped
    # (DECISIONS.md D-010).
    unknown_hours_penalty: float = 0.85

    # price_fit is downweighted when the price tier was imputed (OSM has no
    # price data at all), so an imputed guess never dominates the score.
    imputed_price_weight: float = 0.5

    # Effective-impressions strength of the Beta prior used to smooth
    # internal_score (DECISIONS.md D-009). Centered on the live global
    # right-swipe rate; the eval harness uses the same smoothing.
    score_prior_strength: float = 20.0
    score_prior_mean: float = 0.30


DEFAULT_CONFIG = ScoringConfig()
DEFAULT_CONFIG.weights.validate()
