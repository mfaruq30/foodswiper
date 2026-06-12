"""Synthetic user/venue simulator for offline evaluation (spec §7.4).

THE HONESTY CONTRACT (DECISIONS.md D-007). A synthetic eval is only
meaningful if the ranker cannot trivially recover the data-generating process.
So a synthetic swipe here depends on signals the heuristic ranker is
structurally blind to:

  * `vibe` — a hidden per-venue quality the ranker has no feature for, weighted
    heavily in true utility. No amount of cuisine/price/proximity reasoning can
    recover it, so even a perfect heuristic lands well below the oracle.
  * label noise — a fraction of observed right/left labels are flipped, modeling
    the genuine randomness of real swiping.

Because of these, this harness validates the PLUMBING — metric code, ranker
ordering, the champion/challenger gate — and measures cold-start ranking
quality against a random floor and an oracle ceiling. It is NOT evidence of
real-world lift; that requires logged swipes (see ALGORITHM.md). Anyone citing
a number from here as "lift" is misreading it.
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

# True-utility weights. `vibe` (hidden from the ranker) carries 0.30 — large
# enough that the heuristic's ceiling sits clearly below the oracle's.
_U_CUISINE, _U_PRICE, _U_PROX, _U_VIBE = 0.45, 0.15, 0.10, 0.30
_UTILITY_NOISE_SIGMA = 0.07

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
    """A generated user. `vibe_affinity` is latent and never observed."""

    cuisine_utilities: dict[str, float]
    price_pref: int
    vibe_affinity: float  # HIDDEN
    loved_cuisines: list[str]
    recent_right_cuisines: list[str] = field(default_factory=list)

    def to_profile(self) -> UserProfile:
        # What onboarding + a few swipes actually capture: top cuisines as
        # anchors, a price preference, recent right-swipes. NOT vibe_affinity.
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
    relevance: dict[str, float]  # true utility per id — graded relevance (NDCG)
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


def _true_utility(user: SyntheticUser, venue: SyntheticVenue, rng: random.Random) -> float:
    """Latent probability-of-loving in [0, 1] — includes the hidden vibe term."""
    cuisine_u = user.cuisine_utilities.get(venue.cuisine, 0.0)
    price_u = 1.0 - abs(venue.price_tier - user.price_pref) / 3.0
    # Proximity from box center (where the user sits).
    span = _BOX_HALF_DEG * 2
    prox_u = 1.0 - (abs(venue.lat - _CENTER_LAT) + abs(venue.lon - _CENTER_LON)) / (2 * span)
    vibe_u = user.vibe_affinity * venue.vibe  # HIDDEN from the ranker
    raw = _U_CUISINE * cuisine_u + _U_PRICE * price_u + _U_PROX * prox_u + _U_VIBE * vibe_u
    return min(1.0, max(0.0, raw + rng.gauss(0.0, _UTILITY_NOISE_SIGMA)))


def build_instance(
    rng: random.Random,
    user: SyntheticUser,
    world: list[SyntheticVenue],
    candidates_per_deck: int,
) -> EvalInstance:
    """Sample a deck for one user and attach ground truth + noisy labels."""
    sampled = rng.sample(world, min(candidates_per_deck, len(world)))
    relevance = {venue.id: _true_utility(user, venue, rng) for venue in sampled}

    # Binary "good" set = top fraction by TRUE utility, then flip a fraction of
    # labels to model observation noise (D-007).
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
