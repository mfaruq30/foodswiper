"""The frozen feature contract — train/serve skew protection."""

from app.features import FEATURE_NAMES, extract_features
from app.models import Mode, OpenState, RequestContext, Restaurant, UserProfile


def _restaurant(**kw: object) -> Restaurant:
    base: dict[str, object] = {
        "id": "r",
        "name": "R",
        "cuisines": ["italian"],
        "price_tier": 2,
        "price_imputed": False,
        "lat": 40.7310,
        "lon": -73.9980,
        "metro": "nyc",
        "dietary_tags": [],
        "open_state": OpenState.OPEN,
        "popularity_prior": 0.5,
    }
    base.update(kw)
    return Restaurant(**base)  # type: ignore[arg-type]


def _ctx() -> RequestContext:
    return RequestContext(
        mode=Mode.DINE_IN, metro="nyc", user_lat=40.7308, user_lon=-73.9973, max_distance_m=3000
    )


def test_vector_length_matches_contract() -> None:
    vec = extract_features(_restaurant(), UserProfile(anchor_cuisines=["italian"]), _ctx())
    assert len(vec) == len(FEATURE_NAMES)


def test_features_are_finite_floats() -> None:
    import math

    vec = extract_features(
        _restaurant(internal_impressions=100, internal_rights=70),
        UserProfile(anchor_cuisines=["italian"], price_pref=2, recent_right_cuisines=["italian"]),
        _ctx(),
    )
    assert all(isinstance(v, float) and math.isfinite(v) for v in vec)


def test_anchor_cuisine_feature_fires() -> None:
    idx = FEATURE_NAMES.index("is_anchor_cuisine")
    match = extract_features(
        _restaurant(cuisines=["italian"]), UserProfile(anchor_cuisines=["italian"]), _ctx()
    )
    miss = extract_features(
        _restaurant(cuisines=["bbq"]), UserProfile(anchor_cuisines=["italian"]), _ctx()
    )
    assert match[idx] == 1.0
    assert miss[idx] == 0.0


def test_hours_unknown_feature() -> None:
    idx = FEATURE_NAMES.index("hours_unknown")
    unknown = extract_features(_restaurant(open_state=OpenState.UNKNOWN), UserProfile(), _ctx())
    known = extract_features(_restaurant(open_state=OpenState.OPEN), UserProfile(), _ctx())
    assert unknown[idx] == 1.0
    assert known[idx] == 0.0


def test_recovers_heuristic_components() -> None:
    # The first five features ARE the heuristic components, so the learned
    # ranker strictly supersets the heuristic's information.
    assert FEATURE_NAMES[:5] == (
        "cuisine_affinity",
        "swipe_pattern_match",
        "price_fit",
        "proximity",
        "quality_prior",
    )
