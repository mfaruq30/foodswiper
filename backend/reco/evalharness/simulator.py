"""Synthetic user/venue simulator for offline evaluation (spec §7.4).

THE HONESTY CONTRACT (DECISIONS.md D-007). A synthetic eval is only meaningful
if the ranker cannot trivially recover the data-generating process AND the
ceiling is not a tautology. So:

  * The heuristic sees only a THIN PROJECTION of taste — a few anchor cuisines
    plus a hand-built adjacency map, never each user's full per-cuisine utility
    vector — so it cannot reconstruct true taste even in principle.
  * `vibe` is a hidden per-venue quality with NO ranker feature: one (not the
    only) unrecoverable term in true utility.
  * Observation noise lives only in the BINARY labels (a fraction are flipped),
    modeling the randomness of real swiping — never in the graded relevance.

NDCG is graded against the CLEAN true-utility signal. The oracle ranks by that
same clean signal, so it tops out at NDCG 1.0 by definition — it is an
idealized perfect-knowledge reference, not a production target. The meaningful
number is the heuristic's position ABOVE the random floor; the heuristic sits
below the oracle because of its thin feature projection, NOT because of any one
hidden feature. (An earlier version graded NDCG against a NOISY utility draw,
which made the oracle trivially perfect and falsely attributed the gap to
`vibe`; that is fixed — see DECISIONS.md D-020.)

This harness validates the PLUMBING — metric code, ranker ordering, the gate —
and measures cold-start ranking quality between a random floor and an idealized
ceiling. It is NOT evidence of real-world lift; that needs logged swipes (see
ALGORITHM.md). Anyone citing a number here as "lift" is misreading it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.cuisine_affinity import CANONICAL_CUISINES
from app.models import Mode, OpenState, RequestContext, Restaurant, UserProfile

# Synthetic metro box (~5 km square). Coordinates are arbitrary; only relative
# geometry matters for the proximity term.
_CENTER_LAT, _CENTER_LON = 40.730, -73.990
_BOX_HALF_DEG = 0.025
_MAX_DISTANCE_M = 8000.0

# True-utility weights. `vibe` (hidden from the ranker) carries 0.30 — one of
# several reasons a feature-limited ranker falls short of the oracle.
_U_CUISINE, _U_PRICE, _U_PROX, _U_VIBE = 0.45, 0.15, 0.10, 0.30

_RELEVANT_FRACTION = 0.30  # top 30% of a deck by true utility are "good"
_LABEL_NOISE = 0.15  # fraction of binary labels flipped (observation error)


@dataclass(slots=True)
class SyntheticVenue:
    """A generated venue with one hidden attribute (`vibe`)."""

    id: str
    cuisine: str
    price_tier: int
    lat: float
    lon: float
    popularity_prior: float
    vibe: float  # HIDDEN from the ranker

    def to_restaurant(self) -> Restaurant:
        # The ranker only ever sees this projection — note `vibe` is absent.
        return Restaurant(
            id=self.id,
            name=self.id,
            cuisines=[self.cuisine],
            price_tier=self.price_tier,
            price_imputed=False,
            lat=self.lat,
            lon=self.lon,
            metro="nyc",
            dietary_tags=[],
            open_state=OpenState.OPEN,
            popularity_prior=self.popularity_prior,
        )


@dataclass(slots=True)
class SyntheticUser:
    """A generated user. `vibe_affinity` and the full utility vector are latent."""

    cuisine_utilities: dict[str, float]
    price_pref: int
    vibe_affinity: float  # HIDDEN
    loved_cuisines: list[str]
    recent_right_cuisines: list[str] = field(default_factory=list)

    def to_profile(self) -> UserProfile:
        # What onboarding + a few swipes actually capture: top cuisines as
        # anchors, a price preference, recent right-swipes. NOT vibe_affinity,
        # and NOT the full per-cuisine utility vector — only its top few.
        return UserProfile(
            anchor_cuisines=self.loved_cuisines[:3],
            price_pref=self.price_pref,
            recent_right_cuisines=self.recent_right_cuisines,
        )


@dataclass(slots=True)
class EvalInstance:
    """One deck to rank, with ground truth for scoring."""

    profile: UserProfile
    context: RequestContext
    candidates: list[Restaurant]
    relevance: dict[str, float]  # CLEAN true utility per id — graded by NDCG
    relevant_ids: set[str]  # noisy binary labels (precision/recall/hit/MRR)


def generate_world(rng: random.Random, n_venues: int) -> list[SyntheticVenue]:
    """Create a pool of synthetic venues in the metro box."""
    venues: list[SyntheticVenue] = []
    for index in range(n_venues):
        venues.append(
            SyntheticVenue(
                id=f"v{index:04d}",
                cuisine=rng.choice(CANONICAL_CUISINES),
                price_tier=rng.randint(1, 4),
                lat=_CENTER_LAT + rng.uniform(-_BOX_HALF_DEG, _BOX_HALF_DEG),
                lon=_CENTER_LON + rng.uniform(-_BOX_HALF_DEG, _BOX_HALF_DEG),
                popularity_prior=rng.random(),
                vibe=rng.random(),
            )
        )
    return venues


def generate_users(rng: random.Random, n_users: int) -> list[SyntheticUser]:
    """Create synthetic users with a small set of loved cuisines."""
    users: list[SyntheticUser] = []
    for _ in range(n_users):
        shuffled = list(CANONICAL_CUISINES)
        rng.shuffle(shuffled)
        n_loved = rng.randint(3, 5)
        loved = shuffled[:n_loved]
        utilities = {c: rng.uniform(0.7, 1.0) for c in loved}
        for c in shuffled[n_loved:]:
            utilities[c] = rng.uniform(0.0, 0.3)
        # A few recent right-swipes, realistically drawn from loved cuisines.
        n_recent = rng.randint(0, 4)
        recent = [rng.choice(loved) for _ in range(n_recent)]
        users.append(
            SyntheticUser(
                cuisine_utilities=utilities,
                price_pref=rng.randint(1, 4),
                vibe_affinity=rng.uniform(0.3, 1.0),
                loved_cuisines=loved,
                recent_right_cuisines=recent,
            )
        )
    return users


def expected_utility(user: SyntheticUser, venue: SyntheticVenue) -> float:
    """The user's TRUE, noise-free utility for a venue, in [0, 1].

    This is the clean ground-truth signal NDCG is graded against. It includes
    the hidden `vibe` term and the user's FULL per-cuisine utility vector — both
    of which the ranker only partially observes — so a feature-limited ranker
    cannot reconstruct it even in principle. Deterministic on purpose: the only
    randomness in the eval is the observation noise applied to binary labels in
    `build_instance`. Grading NDCG against a noisy draw would make the oracle
    trivially perfect and the bracket a tautology (D-020).
    """
    cuisine_u = user.cuisine_utilities.get(venue.cuisine, 0.0)
    price_u = 1.0 - abs(venue.price_tier - user.price_pref) / 3.0
    span = _BOX_HALF_DEG * 2
    prox_u = 1.0 - (abs(venue.lat - _CENTER_LAT) + abs(venue.lon - _CENTER_LON)) / (2 * span)
    vibe_u = user.vibe_affinity * venue.vibe  # HIDDEN from the ranker
    raw = _U_CUISINE * cuisine_u + _U_PRICE * price_u + _U_PROX * prox_u + _U_VIBE * vibe_u
    return min(1.0, max(0.0, raw))


def build_instance(
    rng: random.Random,
    user: SyntheticUser,
    world: list[SyntheticVenue],
    candidates_per_deck: int,
) -> EvalInstance:
    """Sample a deck for one user and attach clean truth + noisy labels."""
    sampled = rng.sample(world, min(candidates_per_deck, len(world)))
    # Clean ground-truth utility per venue — what NDCG is graded against.
    relevance = {venue.id: expected_utility(user, venue) for venue in sampled}

    # Binary "good" set = top fraction by true utility, then flip a fraction of
    # labels. The noise lives ONLY in these observed labels, never in the graded
    # relevance above (D-007 / D-020).
    ranked_by_truth = sorted(sampled, key=lambda v: relevance[v.id], reverse=True)
    n_relevant = max(1, round(len(sampled) * _RELEVANT_FRACTION))
    relevant_ids = {venue.id for venue in ranked_by_truth[:n_relevant]}
    for venue in sampled:
        if rng.random() < _LABEL_NOISE:
            if venue.id in relevant_ids:
                relevant_ids.discard(venue.id)
            else:
                relevant_ids.add(venue.id)

    context = RequestContext(
        mode=Mode.DINE_IN,
        metro="nyc",
        user_lat=_CENTER_LAT,
        user_lon=_CENTER_LON,
        max_distance_m=_MAX_DISTANCE_M,
    )
    return EvalInstance(
        profile=user.to_profile(),
        context=context,
        candidates=[venue.to_restaurant() for venue in sampled],
        relevance=relevance,
        relevant_ids=relevant_ids,
    )
