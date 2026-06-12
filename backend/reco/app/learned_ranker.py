"""Layer 4 serving: the LightGBM LambdaMART ranker (spec §7.5, D-008).

Loads a trained model and ranks candidates by predicted relevance using the
frozen feature contract. Two hard rules keep the $0 demo and production safe:

  * `load_learned_ranker` returns None when there is no model file OR LightGBM
    isn't installed — the caller then falls back to the heuristic, so the
    memory-mode demo never needs the `ml` extra (D-019 / D-003 spirit).
  * The model is the CHALLENGER. It serves only where a model is present AND
    promotion has been earned; on synthetic data "earned" means plumbing
    validation only — real promotion needs logged swipes (D-007). The
    heuristic remains the default champion.

LightGBM is imported lazily and typed loosely (no stubs) so mypy --strict and
the core test suite stay LightGBM-free.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .config import DEFAULT_CONFIG, ScoringConfig
from .features import FEATURE_NAMES, extract_features
from .models import RequestContext, Restaurant, UserProfile

if TYPE_CHECKING:
    import lightgbm


class LearnedRanker:
    """Ranks candidates by a trained LightGBM model over the frozen features."""

    def __init__(
        self,
        booster: lightgbm.Booster,
        version: str,
        config: ScoringConfig = DEFAULT_CONFIG,
    ) -> None:
        self._booster = booster
        self.version = version
        self._config = config

    def rank(
        self, user: UserProfile, ctx: RequestContext, candidates: list[Restaurant]
    ) -> list[Restaurant]:
        if not candidates:
            return []
        import numpy as np

        rows = np.asarray(
            [extract_features(c, user, ctx, self._config) for c in candidates], dtype=np.float64
        )
        scores = self._booster.predict(rows)
        ordered = sorted(zip(candidates, scores, strict=True), key=lambda p: p[1], reverse=True)
        return [candidate for candidate, _ in ordered]


def load_learned_ranker(
    model_path: Path, config: ScoringConfig = DEFAULT_CONFIG
) -> LearnedRanker | None:
    """Load a model if present and LightGBM is available; else None (-> heuristic).

    The companion `<model>.meta.json` records the feature contract the model was
    trained against; a mismatch with the current FEATURE_NAMES means the model
    is stale (someone changed features without retraining) and is refused
    rather than silently fed the wrong columns.
    """
    if not model_path.exists():
        return None
    try:
        import lightgbm
    except ImportError:
        return None

    meta_path = model_path.with_suffix(".meta.json")
    version = model_path.stem
    if meta_path.exists():
        meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
        trained_features = meta.get("feature_names")
        if trained_features is not None and tuple(trained_features) != FEATURE_NAMES:
            # Refuse a feature-contract mismatch — fail safe to the heuristic.
            return None
        version = str(meta.get("model_version", version))

    booster = lightgbm.Booster(model_file=str(model_path))
    return LearnedRanker(booster, version, config)
