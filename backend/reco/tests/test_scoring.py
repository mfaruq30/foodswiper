"""Layer 2 heuristic scorer: each signal and the composite."""

from app.config import DEFAULT_CONFIG
from app.models import Mode, OpenState, RequestContext, Restaurant, UserProfile
from app.scoring import (
    HeuristicRanker,
    _weighted_recent_cuisines,
    beta_smoothed_score,
    price_fit,
    proximity_score,
    quality_score,
    score_candidate,
)


def _restaurant(
    rid: str,
    *,
    cuisines: list[str] | None = None,
    price_tier: int = 2,
    price_imputed: bool = False,
    open_state: OpenState = OpenState.OPEN,
    popularity_prior: float = 0.5,
    internal_score: float | None = None,
    impressions: int = 0,
    rights: int = 0,
    lat: float = 40.730,
) -> Restaurant:
    return Restaurant(
        id=rid,
        name=rid,
        cuisines=cuisines or ["italian"],
        price_tier=price_tier,
        price_imputed=price_imputed,
        lat=lat,
        lon=-73.990,
        metro="nyc",
        dietary_tags=[],
        open_state=open_state,
        popularity_prior=popularity_prior,
        internal_score=internal_score,
        internal_impressions=impressions,
        internal_rights=rights,
    )


def _ctx() -> RequestContext:
    return RequestContext(
        mode=Mode.DINE_IN, metro="nyc", user_lat=40.730, user_lon=-73.990, max_distance_m=3000
    )


def test_beta_smoothing_resists_thin_evidence() -> None:
    # 1/1 (one lucky impression) must not outrank 45/60.
    thin = beta_smoothed_score(1, 1, 0.30, 20)
    solid = beta_smoothed_score(45, 60, 0.30, 20)
    assert thin < solid
    # With zero evidence the score is exactly the prior mean.
    assert beta_smoothed_score(0, 0, 0.30, 20) == 0.30


def test_price_fit_policies() -> None:
    user_matched = UserProfile(price_pref=2)
    assert price_fit(_restaurant("a", price_tier=2), user_matched, DEFAULT_CONFIG) == 1.0
    # No preference -> neutral.
    assert price_fit(_restaurant("b"), UserProfile(), DEFAULT_CONFIG) == 0.5
    # Imputed price is blended toward neutral, so a perfect raw match is damped.
    imputed = price_fit(
        _restaurant("c", price_tier=2, price_imputed=True), user_matched, DEFAULT_CONFIG
    )
    assert 0.5 < imputed < 1.0


def test_quality_prior_source_switches_with_evidence() -> None:
    cold = _restaurant("cold", popularity_prior=0.42)
    warm = _restaurant("warm", popularity_prior=0.42, impressions=100, rights=90)
    user = UserProfile(anchor_cuisines=["italian"])
    cold_scored = score_candidate(cold, user, _ctx())
    warm_scored = score_candidate(warm, user, _ctx())
    # Cold start uses the open-data prior; warm uses the (high) swipe signal.
    assert cold_scored.components["quality_prior"] == 0.42
    # 90/100 right-swipes, Beta-smoothed -> (90+6)/(100+20) = 0.80, well above
    # the 0.42 open-data prior: the signal source has switched.
    assert warm_scored.components["quality_prior"] >= 0.8


def test_unknown_hours_penalty_lowers_score() -> None:
    user = UserProfile(anchor_cuisines=["italian"])
    open_scored = score_candidate(_restaurant("open"), user, _ctx())
    unknown_scored = score_candidate(
        _restaurant("unknown", open_state=OpenState.UNKNOWN), user, _ctx()
    )
    assert unknown_scored.score < open_scored.score
    assert 0.0 <= unknown_scored.score <= 1.0


def test_ranker_orders_better_match_first() -> None:
    user = UserProfile(anchor_cuisines=["italian"], price_pref=2)
    great = _restaurant("great", cuisines=["italian"], price_tier=2)
    poor = _restaurant("poor", cuisines=["bbq"], price_tier=4)
    ordered = HeuristicRanker().rank(user, _ctx(), [poor, great])
    assert [r.id for r in ordered] == ["great", "poor"]


def test_weighted_recent_cuisines_decays_by_recency() -> None:
    # Most-recent cuisine weighs 1.0, the next 0.85, and so on.
    weights = _weighted_recent_cuisines(["italian", "bbq"])
    assert weights["italian"] == 1.0
    assert weights["bbq"] == 0.85
    # A cuisine appearing twice keeps its most-recent (higher) weight.
    deduped = _weighted_recent_cuisines(["italian", "bbq", "italian"])
    assert deduped["italian"] == 1.0


def test_swipe_pattern_match_lifts_recently_swiped_cuisine() -> None:
    # Two otherwise-identical candidates; the user has been right-swiping sushi.
    # The dynamic swipe-pattern term must raise the sushi candidate's score.
    user = UserProfile(anchor_cuisines=["italian"], recent_right_cuisines=["sushi"])
    sushi = _restaurant("sushi", cuisines=["sushi"])
    burger = _restaurant("burger", cuisines=["burger"])
    sushi_scored = score_candidate(sushi, user, _ctx())
    burger_scored = score_candidate(burger, user, _ctx())
    assert sushi_scored.components["swipe_pattern_match"] > 0.0
    assert burger_scored.components["swipe_pattern_match"] == 0.0
    assert sushi_scored.score > burger_scored.score


def test_explicit_cuisine_weights_take_precedence_over_anchors() -> None:
    # When learned cuisine_weights exist they drive ranking, not the anchors.
    user = UserProfile(cuisine_weights={"bbq": 1.0}, anchor_cuisines=["italian"])
    bbq = _restaurant("bbq", cuisines=["bbq"])
    italian = _restaurant("italian", cuisines=["italian"])
    ordered = HeuristicRanker().rank(user, _ctx(), [italian, bbq])
    assert [r.id for r in ordered] == ["bbq", "italian"]


def test_persisted_internal_score_overrides_live_counts() -> None:
    # A precomputed internal_score (the decayed, weekly-recomputed posterior the
    # data layer persists) must win over a live count recompute (D-009) — the
    # Phase-3 wiring trap the reviewers flagged.
    r = _restaurant("r", internal_score=0.95, impressions=100, rights=10)
    assert quality_score(r, DEFAULT_CONFIG) == 0.95


def test_proximity_handles_degenerate_zero_radius() -> None:
    # A 0 m radius must score 0, not raise ZeroDivisionError.
    ctx = RequestContext(
        mode=Mode.DINE_IN, metro="nyc", user_lat=40.730, user_lon=-73.990, max_distance_m=0.0
    )
    assert proximity_score(_restaurant("r"), ctx) == 0.0


def test_out_of_range_quality_inputs_are_clamped() -> None:
    # A malformed persisted score outside [0,1] must not escape the bound.
    assert quality_score(_restaurant("hi", internal_score=1.7), DEFAULT_CONFIG) == 1.0
    assert quality_score(_restaurant("lo", popularity_prior=-0.5), DEFAULT_CONFIG) == 0.0
