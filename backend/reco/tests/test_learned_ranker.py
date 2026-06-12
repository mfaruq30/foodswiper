"""Layer 4 dataset assembly + serving. LightGBM tests skip if the ml extra
is absent, so the core $0 path never depends on it."""

import json
from pathlib import Path

import pytest

from app.models import Mode, OpenState, RequestContext, Restaurant, UserProfile
from learnedranker.dataset import build_synthetic_dataset, split_by_group

lightgbm = pytest.importorskip("lightgbm")


def test_dataset_groups_sum_to_rows() -> None:
    data = build_synthetic_dataset(seed=1, n_users=20, n_venues=80, candidates_per_deck=30)
    assert sum(data.groups) == len(data.features) == len(data.labels)
    assert len(data.groups) == 20  # one group per served deck (D-008)


def test_labels_use_the_d008_gain_classes() -> None:
    data = build_synthetic_dataset(seed=2, n_users=40, n_venues=120, candidates_per_deck=30)
    classes = set(data.labels)
    # left=0, right=1, conversion=2 — the [0,1,5] gain structure.
    assert classes <= {0, 1, 2}
    assert 2 in classes  # some right-swipes convert (the stronger positive)


def test_split_keeps_decks_whole() -> None:
    data = build_synthetic_dataset(seed=3, n_users=50, n_venues=120, candidates_per_deck=30)
    train, val = split_by_group(data, validation_fraction=0.2, seed=3)
    assert len(train.groups) + len(val.groups) == len(data.groups)
    assert sum(train.groups) == len(train.features)
    assert sum(val.groups) == len(val.features)
    # Every deck stays intact (sizes preserved, none torn).
    assert sorted(train.groups + val.groups) == sorted(data.groups)


def _restaurant(rid: str, cuisine: str, *, impressions: int = 0, rights: int = 0) -> Restaurant:
    return Restaurant(
        id=rid,
        name=rid,
        cuisines=[cuisine],
        price_tier=2,
        price_imputed=False,
        lat=40.7310,
        lon=-73.9980,
        metro="nyc",
        dietary_tags=[],
        open_state=OpenState.OPEN,
        popularity_prior=0.5,
        internal_impressions=impressions,
        internal_rights=rights,
    )


def test_serving_round_trip_and_feature_contract_guard(tmp_path: Path) -> None:
    from app.features import FEATURE_NAMES
    from app.learned_ranker import load_learned_ranker
    from learnedranker.train import train

    model_path = tmp_path / "m.txt"
    train(
        seed=7,
        n_users=300,
        n_venues=200,
        candidates_per_deck=30,
        num_rounds=60,
        model_path=model_path,
    )

    ranker = load_learned_ranker(model_path)
    assert ranker is not None
    user = UserProfile(anchor_cuisines=["italian"], price_pref=2)
    ctx = RequestContext(
        mode=Mode.DINE_IN, metro="nyc", user_lat=40.7308, user_lon=-73.9973, max_distance_m=3000
    )
    ordered = ranker.rank(user, ctx, [_restaurant("a", "italian"), _restaurant("b", "bbq")])
    assert {r.id for r in ordered} == {"a", "b"}  # ranks the candidate set, no drops/dupes

    # A feature-contract mismatch must be REFUSED (fail safe to heuristic).
    meta = json.loads(model_path.with_suffix(".meta.json").read_text())
    meta["feature_names"] = [*FEATURE_NAMES, "an_extra_feature"]
    model_path.with_suffix(".meta.json").write_text(json.dumps(meta))
    assert load_learned_ranker(model_path) is None


def test_missing_model_returns_none(tmp_path: Path) -> None:
    from app.learned_ranker import load_learned_ranker

    assert load_learned_ranker(tmp_path / "nope.txt") is None
