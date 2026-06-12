"""Simulator ground-truth properties the D-007/D-020 honesty contract relies on."""

from evalharness.simulator import SyntheticUser, SyntheticVenue, expected_utility


def _user(vibe_affinity: float) -> SyntheticUser:
    return SyntheticUser(
        cuisine_utilities={"italian": 0.9},
        price_pref=2,
        vibe_affinity=vibe_affinity,
        loved_cuisines=["italian", "pizza", "bbq"],
    )


def _venue(vibe: float) -> SyntheticVenue:
    return SyntheticVenue(
        id="v",
        cuisine="italian",
        price_tier=2,
        lat=40.730,
        lon=-73.990,
        popularity_prior=0.5,
        vibe=vibe,
    )


def test_expected_utility_is_deterministic() -> None:
    # The graded signal carries NO randomness (the D-020 fix): two calls agree,
    # so the oracle's perfection is by definition, not by chasing a noisy draw.
    user, venue = _user(0.8), _venue(0.6)
    assert expected_utility(user, venue) == expected_utility(user, venue)


def test_vibe_moves_true_utility_but_is_absent_from_the_projection() -> None:
    user = _user(1.0)
    # vibe changes ground-truth utility...
    assert expected_utility(user, _venue(1.0)) > expected_utility(user, _venue(0.0))
    # ...but the Restaurant projection the ranker sees has no vibe field at all.
    projected = _venue(0.9).to_restaurant()
    assert not hasattr(projected, "vibe")
