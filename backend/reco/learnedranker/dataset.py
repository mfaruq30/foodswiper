"""Assemble LambdaMART training data with the D-008 group/label structure.

Group = one served deck (one EvalInstance / reco_event). Labels follow the
D-008 gain mapping: left-swipe 0, right-swipe 1, conversion 2 (label_gain
[0, 1, 5]). Unseen cards are never emitted (they have no label) — labeling
them negative is the classic swipe-app logging bug D-008 calls out.

Two sources, one shape:
  * synthetic — derived from the eval simulator (what we have pre-launch);
  * FUTURE(Phase 7) `from_reco_events` — the same (features, label, group)
    shape joined from logged swipes once they exist. Stubbed with the exact
    contract so the real loader is a drop-in.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.features import extract_features
from evalharness.simulator import build_instance, generate_users, generate_world


@dataclass(slots=True)
class RankingDataset:
    """LightGBM-ready: a flat feature matrix, labels, and per-deck group sizes.

    `features[i]` belongs to group g where g is found by walking `groups`
    (the sizes sum to len(features)). Splitting is by group, never by row,
    so a deck is never torn across train/val.
    """

    features: list[list[float]]
    labels: list[int]
    groups: list[int]

    def __len__(self) -> int:
        return len(self.groups)


# Fraction of a deck's right-swipes (the top by true utility) that also
# "convert" — the stronger positive (label 2). Models the funnel: some likes
# become outbound taps.
_CONVERSION_FRACTION = 0.25


def build_synthetic_dataset(
    seed: int, n_users: int, n_venues: int, candidates_per_deck: int
) -> RankingDataset:
    """Generate decks and turn each into (features, graded label, group).

    Label derivation from the simulator's ground truth: a card in the deck's
    noisy relevant set is a right-swipe (label 1); the strongest of those (top
    by clean utility) additionally convert (label 2); the rest are left-swipes
    (label 0). This reproduces the [0,1,5]-gain structure on observable data.
    """
    rng = random.Random(seed)
    world = generate_world(rng, n_venues)
    users = generate_users(rng, n_users)

    features: list[list[float]] = []
    labels: list[int] = []
    groups: list[int] = []

    for user_model, user in ((u, u.to_profile()) for u in users):
        instance = build_instance(rng, user_model, world, candidates_per_deck)
        # Rank this deck's relevant cards by clean utility to pick converters.
        relevant_sorted = sorted(
            instance.relevant_ids,
            key=lambda cid: instance.relevance.get(cid, 0.0),
            reverse=True,
        )
        n_convert = int(len(relevant_sorted) * _CONVERSION_FRACTION)
        converters = set(relevant_sorted[:n_convert])

        deck_size = 0
        for candidate in instance.candidates:
            if candidate.id in converters:
                label = 2
            elif candidate.id in instance.relevant_ids:
                label = 1
            else:
                label = 0
            features.append(extract_features(candidate, user, instance.context))
            labels.append(label)
            deck_size += 1
        groups.append(deck_size)

    return RankingDataset(features=features, labels=labels, groups=groups)


def split_by_group(
    dataset: RankingDataset, validation_fraction: float, seed: int
) -> tuple[RankingDataset, RankingDataset]:
    """Hold out whole decks (D-008: never split a deck across the boundary).

    The split is RANDOM by deck. D-008 mandates a TEMPORAL split on real data
    (never leak future swipes into the past); the synthetic source has no time
    axis, so temporal splitting is deferred to the real `from_reco_events`
    loader (D-023 pre-promotion item #3).
    """
    if len(dataset.groups) < 2:
        raise ValueError("need at least 2 decks to split")
    rng = random.Random(seed)
    deck_indices = list(range(len(dataset.groups)))
    rng.shuffle(deck_indices)
    # Clamp so neither side is empty — an empty train set fails opaquely deep
    # inside LightGBM. (Synthetic runs are large; this guards the real loader.)
    n_val = min(max(1, int(len(deck_indices) * validation_fraction)), len(deck_indices) - 1)
    val_decks = set(deck_indices[:n_val])

    # Row offsets per deck, to slice the flat matrix back into decks.
    offsets: list[int] = []
    running = 0
    for size in dataset.groups:
        offsets.append(running)
        running += size

    def subset(keep_val: bool) -> RankingDataset:
        feats: list[list[float]] = []
        labs: list[int] = []
        grps: list[int] = []
        for deck, (offset, size) in enumerate(zip(offsets, dataset.groups, strict=True)):
            if (deck in val_decks) != keep_val:
                continue
            feats.extend(dataset.features[offset : offset + size])
            labs.extend(dataset.labels[offset : offset + size])
            grps.append(size)
        return RankingDataset(features=feats, labels=labs, groups=grps)

    return subset(False), subset(True)
