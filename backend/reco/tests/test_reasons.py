"""Templated reasons: honest, specific, and never contradicting the card."""

from app.models import Mode, OpenState, RequestContext, Restaurant, UserProfile
from app.reasons import templated_reason


def _restaurant(cuisine: str, internal_score: float | None = None) -> Restaurant:
    return Restaurant(
        id="r",
        name="Test",
        cuisines=[cuisine],
        price_tier=2,
        price_imputed=False,
        lat=40.7350,
        lon=-73.9973,
        metro="nyc",
        dietary_tags=[],
        open_state=OpenState.OPEN,
        popularity_prior=0.5,
        internal_score=internal_score,
    )


def _ctx() -> RequestContext:
    return RequestContext(
        mode=Mode.DINE_IN, metro="nyc", user_lat=40.7308, user_lon=-73.9973, max_distance_m=3000
    )


def test_direct_taste_match_leads() -> None:
    user = UserProfile(anchor_cuisines=["pizza"])
    reason = templated_reason(_restaurant("pizza"), user, _ctx())
    assert "You love Pizza" in reason
    assert "mi" in reason  # always carries the concrete distance


def test_adjacent_cuisine_is_named_as_a_cousin() -> None:
    user = UserProfile(anchor_cuisines=["japanese"])
    reason = templated_reason(_restaurant("sushi"), user, _ctx())
    assert "Japanese" in reason
    assert "Sushi" in reason


def test_crowd_signal_used_when_no_taste_link() -> None:
    user = UserProfile(anchor_cuisines=["mexican"])
    reason = templated_reason(_restaurant("german", internal_score=0.87), user, _ctx())
    assert "87%" in reason


def test_fallback_is_still_specific() -> None:
    user = UserProfile()  # no taste at all
    reason = templated_reason(_restaurant("german"), user, _ctx())
    assert "German" in reason
    assert "mi" in reason
