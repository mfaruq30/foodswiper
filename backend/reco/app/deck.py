"""Deck assembly (D-009): scoring -> exploration -> diversity -> served deck.

This sits ON TOP of the Layer-2 scorer and is where the anti-rich-get-richer
mechanics live:

  * Thompson sampling on the quality signal: rank by a draw from
    Beta(alpha + rights, beta + lefts) instead of the posterior mean, so
    low-evidence venues naturally win some impressions.
  * Explore slots: a fixed number of deck positions reserved for under-shown /
    novel-cuisine candidates, each flagged `explore=True` in the log — the flag
    is what makes unbiased offline evaluation possible later (D-008).
  * Diversity cap: at most N cards per cuisine per deck (MMR-lite).

Randomness is injected (`random.Random`) so every behavior is deterministic
under test.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .config import DEFAULT_CONFIG, ScoringConfig
from .models import OpenState, RequestContext, Restaurant, UserProfile
from .scoring import score_candidate

DECK_SIZE = 10
EXPLORE_SLOTS = 2  # of DECK_SIZE (epsilon = 0.2, D-009)
MAX_PER_CUISINE = 3


@dataclass(slots=True)
class DeckCard:
    """One card as served: the venue, its provenance, and its reason text."""

    restaurant: Restaurant
    position: int
    explore: bool
    score: float
    reason: str


def _thompson_quality(restaurant: Restaurant, config: ScoringConfig, rng: random.Random) -> float:
    """A posterior draw for the venue's quality instead of its mean (D-009).

    Rights are clamped to impressions at the data boundary: corrupt counters
    (rights > impressions) would otherwise drive beta toward the 1e-9 floor and
    pin every draw at exactly 1.0 — a silent, permanent top-of-deck.
    """
    impressions = max(0, restaurant.internal_impressions)
    rights = max(0, min(restaurant.internal_rights, impressions))
    alpha = config.score_prior_mean * config.score_prior_strength + rights
    beta = (1.0 - config.score_prior_mean) * config.score_prior_strength + impressions - rights
    return rng.betavariate(max(alpha, 1e-9), max(beta, 1e-9))


def _exploit_order(
    candidates: list[Restaurant],
    user: UserProfile,
    ctx: RequestContext,
    config: ScoringConfig,
    rng: random.Random,
) -> list[tuple[Restaurant, float]]:
    """Heuristic score, with the quality term resampled via a Thompson draw —
    but ONLY for venues that have swipe evidence to resample.

    Why the guard: at launch every venue has zero impressions, and substituting
    a prior-only Beta draw for the quality component would replace the
    open-data popularity prior with pure noise (and, interacting with the
    unknown-hours penalty, actually INVERT it — verified by simulation in the
    Phase 3 review). Cold venues keep their deterministic prior; exploration
    slots, not score noise, are the cold-exposure mechanism (D-009).
    """
    ordered: list[tuple[Restaurant, float]] = []
    for candidate in candidates:
        scored = score_candidate(candidate, user, ctx, config)
        adjusted = scored.score
        if candidate.internal_impressions > 0:
            # The penalty multiplies the whole composite in score_candidate, so
            # the substituted draw must carry the same factor or the swap
            # changes more than the quality term.
            penalty = (
                config.unknown_hours_penalty if candidate.open_state is OpenState.UNKNOWN else 1.0
            )
            adjusted += (
                penalty
                * config.weights.quality_prior
                * (_thompson_quality(candidate, config, rng) - scored.components["quality_prior"])
            )
        ordered.append((candidate, adjusted))
    ordered.sort(key=lambda pair: pair[1], reverse=True)
    return ordered


def _explore_pick(
    pool: list[Restaurant],
    taken: set[str],
    user_top_cuisines: set[str],
    cuisine_counts: dict[str, int],
    rng: random.Random,
) -> Restaurant | None:
    """Pick an exploration candidate: least-shown first, novel cuisine preferred.

    Weighting by impression deficit gives unshown venues their first exposure
    (breaking the impression-starvation loop); preferring cuisines outside the
    user's current top tastes widens the preference estimate's support (D-009).
    The per-cuisine cap applies here too — exploration must add diversity, not
    re-stack the cuisine the cap just throttled.
    """
    available = [
        r
        for r in pool
        if r.id not in taken
        and cuisine_counts.get(r.cuisines[0] if r.cuisines else "", 0) < MAX_PER_CUISINE
    ]
    if not available:
        return None
    novel = [r for r in available if not set(r.cuisines) & user_top_cuisines]
    shortlist = novel or available
    min_impressions = min(r.internal_impressions for r in shortlist)
    least_shown = [r for r in shortlist if r.internal_impressions == min_impressions]
    return rng.choice(least_shown)


def assemble_deck(
    candidates: list[Restaurant],
    user: UserProfile,
    ctx: RequestContext,
    rng: random.Random,
    config: ScoringConfig = DEFAULT_CONFIG,
    deck_size: int = DECK_SIZE,
    explore_slots: int = EXPLORE_SLOTS,
) -> list[DeckCard]:
    """Build the served deck from hard-filtered candidates.

    Exploit positions (deck_size - explore_slots) fill in Thompson-adjusted
    score order under the per-cuisine cap; then EXACTLY up to `explore_slots`
    exploration picks follow from the least-shown / novel-cuisine pool. When
    the cap or a thin candidate pool throttles exploit, the deck comes out
    shorter — explore never expands to fill the gap (that would silently turn
    a diversity guard into an exploration flood), and nothing is padded or
    duplicated.
    """
    from .reasons import templated_reason  # local import: avoids a module cycle

    ordered = _exploit_order(candidates, user, ctx, config, rng)
    user_top = set(user.anchor_cuisines[:2]) | set(user.recent_right_cuisines[:2])

    cards: list[DeckCard] = []
    taken: set[str] = set()
    cuisine_counts: dict[str, int] = {}

    exploit_target = max(0, deck_size - explore_slots)
    for restaurant, score in ordered:
        if len(cards) >= exploit_target:
            break
        # Diversity cap: a venue only counts against its FIRST cuisine — the
        # one the card displays — so multi-tagged venues aren't over-throttled.
        primary = restaurant.cuisines[0] if restaurant.cuisines else ""
        if cuisine_counts.get(primary, 0) >= MAX_PER_CUISINE:
            continue
        cards.append(
            DeckCard(
                restaurant=restaurant,
                position=len(cards),
                explore=False,
                score=score,
                reason=templated_reason(restaurant, user, ctx),
            )
        )
        taken.add(restaurant.id)
        cuisine_counts[primary] = cuisine_counts.get(primary, 0) + 1

    for _ in range(explore_slots):
        pick = _explore_pick(candidates, taken, user_top, cuisine_counts, rng)
        if pick is None:
            break
        cards.append(
            DeckCard(
                restaurant=pick,
                position=len(cards),
                explore=True,
                score=0.0,  # explore cards are exposure bets, not score claims
                reason=templated_reason(pick, user, ctx),
            )
        )
        taken.add(pick.id)
        primary = pick.cuisines[0] if pick.cuisines else ""
        cuisine_counts[primary] = cuisine_counts.get(primary, 0) + 1
    return cards
