"""Deck assembly: exploration slots, diversity cap, determinism (D-009)."""

import random

from app.deck import assemble_deck
from app.models import Mode, OpenState, RequestContext, Restaurant, UserProfile


def _restaurant(
    rid: str,
    cuisine: str,
    *,
    impressions: int = 50,
    rights: int = 25,
    popularity: float = 0.5,
) -> Restaurant:
    return Restaurant(
        id=rid,
        name=rid,
        cuisines=[cuisine],
        price_tier=2,
        price_imputed=False,
        lat=40.730,
        lon=-73.990,
        metro="nyc",
        dietary_tags=[],
        open_state=OpenState.OPEN,
        popularity_prior=popularity,
        internal_impressions=impressions,
        internal_rights=rights,
    )


def _ctx() -> RequestContext:
    return RequestContext(
        mode=Mode.DINE_IN, metro="nyc", user_lat=40.730, user_lon=-73.990, max_distance_m=5000
    )


def _user() -> UserProfile:
    return UserProfile(anchor_cuisines=["italian"])


def _pool() -> list[Restaurant]:
    """12 italian (user favorite, cap-throttled), 6 strong distinct-cuisine
    venues (enough to fill exploit), one never-shown thai with a weak prior."""
    pool = [_restaurant(f"it{i}", "italian") for i in range(12)]
    for cuisine in ("bbq", "mexican", "sushi", "french", "indian", "greek"):
        pool.append(_restaurant(f"{cuisine}1", cuisine, popularity=0.9, rights=40))
    pool.append(_restaurant("thai_new", "thai", impressions=0, rights=0, popularity=0.05))
    return pool


def test_deck_fills_with_exactly_two_explore_slots() -> None:
    cards = assemble_deck(_pool(), _user(), _ctx(), random.Random(7))
    assert len(cards) == 10
    assert sum(1 for c in cards if c.explore) == 2
    # Explore cards sit at the end; positions are sequential.
    assert all(not c.explore for c in cards[:8])
    assert [c.position for c in cards] == list(range(10))


def test_cuisine_cap_holds_across_the_whole_deck() -> None:
    # 12 italian venues available and the user loves italian — but exploit AND
    # explore together may carry at most 3 (D-009 diversity guard).
    cards = assemble_deck(_pool(), _user(), _ctx(), random.Random(7))
    italian = [c for c in cards if c.restaurant.cuisines == ["italian"]]
    assert len(italian) == 3


def test_explore_gives_never_shown_venue_first_exposure() -> None:
    # thai_new: zero impressions, weak prior (so exploit ranks it last), novel
    # cuisine. Exploration exists precisely to surface it anyway.
    cards = assemble_deck(_pool(), _user(), _ctx(), random.Random(7))
    explore_ids = {c.restaurant.id for c in cards if c.explore}
    assert "thai_new" in explore_ids


def test_explore_never_floods_when_exploit_is_throttled() -> None:
    # Only italian venues available: cap limits exploit to 3, and explore must
    # NOT expand to fill the deck with more italians — it is capped too.
    italians = [_restaurant(f"it{i}", "italian") for i in range(12)]
    cards = assemble_deck(italians, _user(), _ctx(), random.Random(7))
    assert len(cards) == 3
    assert all(not c.explore for c in cards)


def test_no_duplicates_and_short_pool_yields_short_deck() -> None:
    small = [_restaurant("a", "italian"), _restaurant("b", "bbq")]
    cards = assemble_deck(small, _user(), _ctx(), random.Random(1))
    ids = [c.restaurant.id for c in cards]
    assert len(ids) == len(set(ids)) == 2  # never padded, never duplicated


def test_same_seed_same_deck() -> None:
    a = assemble_deck(_pool(), _user(), _ctx(), random.Random(42))
    b = assemble_deck(_pool(), _user(), _ctx(), random.Random(42))
    assert [c.restaurant.id for c in a] == [c.restaurant.id for c in b]


def test_every_card_has_a_reason() -> None:
    cards = assemble_deck(_pool(), _user(), _ctx(), random.Random(7))
    assert all(c.reason for c in cards)
