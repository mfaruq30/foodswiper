"""Train the LambdaMART challenger: ``python -m learnedranker.train``.

Writes the model + a sidecar meta.json (the feature contract + version) that
serving checks before trusting the model. Deterministic given the seed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.features import FEATURE_NAMES

from .dataset import RankingDataset, build_synthetic_dataset, split_by_group

DEFAULT_SEED = 20260612
DEFAULT_MODEL_PATH = Path("models/learned_ranker.txt")

# LambdaMART params. label_gain = [0, 1, 5] encodes the D-008 label mapping
# (left/right/conversion); kept small/conservative — this is a few-feature
# ranker on synthetic data, not a place to chase capacity.
_PARAMS: dict[str, Any] = {
    "objective": "lambdarank",
    "metric": "ndcg",
    "ndcg_eval_at": [5],
    "label_gain": [0, 1, 5],
    "learning_rate": 0.05,
    "num_leaves": 15,
    "min_data_in_leaf": 30,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.9,
    "bagging_freq": 1,
    "verbose": -1,
}


def _to_lgb_dataset(data: RankingDataset, reference: Any = None) -> Any:
    import lightgbm
    import numpy as np

    # LightGBM wants an ndarray feature matrix (numpy ships with it); features
    # stay pure-Python lists everywhere else for testability.
    return lightgbm.Dataset(
        np.asarray(data.features, dtype=np.float64),
        label=np.asarray(data.labels, dtype=np.int32),
        group=np.asarray(data.groups, dtype=np.int32),
        reference=reference,
    )


def train(
    seed: int = DEFAULT_SEED,
    n_users: int = 1500,
    n_venues: int = 400,
    candidates_per_deck: int = 40,
    num_rounds: int = 300,
    model_path: Path = DEFAULT_MODEL_PATH,
) -> Path:
    """Train on synthetic decks; early-stop on a held-out deck split."""
    import lightgbm

    full = build_synthetic_dataset(seed, n_users, n_venues, candidates_per_deck)
    train_set, val_set = split_by_group(full, validation_fraction=0.2, seed=seed)

    lgb_train = _to_lgb_dataset(train_set)
    lgb_val = _to_lgb_dataset(val_set, reference=lgb_train)

    booster = lightgbm.train(
        _PARAMS,
        lgb_train,
        num_boost_round=num_rounds,
        valid_sets=[lgb_val],
        callbacks=[lightgbm.early_stopping(30, verbose=False), lightgbm.log_evaluation(0)],
    )

    model_path.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(model_path), num_iteration=booster.best_iteration)

    meta = {
        "model_version": f"lgbm-lambdamart-{seed}",
        "feature_names": list(FEATURE_NAMES),
        "trained_on": "synthetic",  # D-007: plumbing validation, not real lift
        "seed": seed,
        "best_iteration": booster.best_iteration,
        "n_train_decks": len(train_set.groups),
        "n_val_decks": len(val_set.groups),
    }
    model_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    print(f"saved {model_path} (best_iteration={booster.best_iteration})")
    return model_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    args = parser.parse_args(argv)
    train(seed=args.seed, model_path=args.model_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
