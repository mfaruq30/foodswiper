"""Taste archetype keys — the LLM reason cache's low-cardinality key (D-004)."""

from app.archetype import archetype_key
from app.models import UserProfile


def test_cold_start_users_share_one_archetype() -> None:
    assert archetype_key(UserProfile()) == "new"


def test_top_cuisines_define_the_key_deterministically() -> None:
    user = UserProfile(cuisine_weights={"italian": 0.9, "ramen": 0.7, "bbq": 0.2})
    # Top two by weight, joined — stable across calls.
    assert archetype_key(user) == "italian+ramen"
    assert archetype_key(user) == archetype_key(user)


def test_ties_break_alphabetically() -> None:
    user = UserProfile(cuisine_weights={"sushi": 0.8, "pizza": 0.8})
    assert archetype_key(user) == "pizza+sushi"


def test_anchors_drive_the_key_when_no_weights() -> None:
    user = UserProfile(anchor_cuisines=["thai", "korean"])
    # anchors map to weight 1.0 each; alphabetical tie-break.
    assert archetype_key(user) == "korean+thai"
