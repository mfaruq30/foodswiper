"""Cuisine adjacency: the cold-start backbone (spec §7.3, DECISIONS.md D-009).

A new user has named a few anchor restaurants and picked cuisines — nothing
else. Adjacency generalizes that thin signal: someone who loves Sichuan
probably likes other Chinese and pan-Asian food; a trattoria lover likes
Mediterranean. This is a hand-built, versioned map over the canonical cuisine
nodes (`CANONICAL_CUISINES`, ~50, derived from the edge list below) — NOT
learned embeddings, which would
need interaction data we don't have at launch and would produce
plausible-but-unvalidated neighbors. The data-driven upgrade (co-preference
from real swipes) is a post-launch task, gated on data volume.

Map version history:
  1 — initial hand-built map, Phase 2.
"""

from __future__ import annotations

AFFINITY_MAP_VERSION = 1

# Self-affinity (a cuisine to itself) is always 1.0 and implicit.
_NEAR = 0.6  # close neighbor: strong cross-preference
_RELATED = 0.3  # related: mild cross-preference

# Undirected edges declared once; the lookup below is symmetrized. Grouped by
# culinary cluster so the reasoning is auditable in review (it is reviewed in
# PR like code, per D-009).
_EDGES: list[tuple[str, str, float]] = [
    # East / Southeast Asian
    ("japanese", "sushi", _NEAR),
    ("japanese", "ramen", _NEAR),
    ("japanese", "pan_asian", _NEAR),
    ("japanese", "korean", _RELATED),
    ("sushi", "ramen", _RELATED),
    ("ramen", "noodles", _NEAR),
    ("ramen", "korean", _RELATED),
    ("chinese", "noodles", _NEAR),
    ("chinese", "pan_asian", _NEAR),
    ("chinese", "thai", _RELATED),
    ("chinese", "vietnamese", _RELATED),
    ("thai", "vietnamese", _NEAR),
    ("thai", "pan_asian", _NEAR),
    ("thai", "noodles", _RELATED),
    ("vietnamese", "noodles", _NEAR),
    ("vietnamese", "pan_asian", _NEAR),
    ("korean", "pan_asian", _NEAR),
    ("korean", "bbq", _RELATED),
    ("pan_asian", "noodles", _RELATED),
    ("filipino", "pan_asian", _NEAR),
    # Italian / Mediterranean / Middle Eastern
    ("italian", "pizza", _NEAR),
    ("italian", "mediterranean", _NEAR),
    ("italian", "french", _RELATED),
    ("mediterranean", "greek", _NEAR),
    ("mediterranean", "middle_eastern", _NEAR),
    ("mediterranean", "spanish", _RELATED),
    ("greek", "middle_eastern", _NEAR),
    ("greek", "turkish", _RELATED),
    ("middle_eastern", "turkish", _NEAR),
    ("middle_eastern", "halal", _NEAR),
    ("halal", "indian", _RELATED),
    ("french", "bakery", _RELATED),
    # Latin
    ("mexican", "latin", _NEAR),
    ("mexican", "caribbean", _RELATED),
    ("latin", "caribbean", _NEAR),
    ("latin", "peruvian", _NEAR),
    ("latin", "spanish", _RELATED),
    ("peruvian", "seafood", _RELATED),
    # American comfort / Southern
    ("american", "burger", _NEAR),
    ("american", "diner", _NEAR),
    ("american", "bbq", _RELATED),
    ("american", "southern", _RELATED),
    ("burger", "diner", _RELATED),
    ("burger", "sandwich", _RELATED),
    ("diner", "breakfast", _NEAR),
    ("breakfast", "bakery", _RELATED),
    ("breakfast", "coffee", _RELATED),
    ("bbq", "southern", _NEAR),
    ("bbq", "chicken", _RELATED),
    ("southern", "chicken", _NEAR),
    ("southern", "cajun", _NEAR),
    ("cajun", "seafood", _RELATED),
    ("chicken", "american", _RELATED),
    # Sandwiches / delis / greens
    ("sandwich", "deli", _NEAR),
    ("sandwich", "salad", _RELATED),
    ("deli", "bagel", _RELATED),
    ("deli", "kosher", _RELATED),
    ("bagel", "breakfast", _RELATED),
    ("salad", "vegetarian", _NEAR),
    ("salad", "vegan", _RELATED),
    ("vegetarian", "vegan", _NEAR),
    ("vegetarian", "indian", _RELATED),
    ("vegetarian", "ethiopian", _RELATED),
    # Sweets / drinks
    ("dessert", "bakery", _NEAR),
    ("dessert", "coffee", _RELATED),
    ("dessert", "bubble_tea", _RELATED),
    ("bakery", "coffee", _RELATED),
    ("coffee", "bubble_tea", _RELATED),
    ("bubble_tea", "juice", _RELATED),
    ("juice", "vegan", _RELATED),
    # Misc bridges
    ("indian", "middle_eastern", _RELATED),
    ("seafood", "mediterranean", _RELATED),
    ("steakhouse", "american", _RELATED),
    ("steakhouse", "seafood", _RELATED),
    ("german", "eastern_european", _NEAR),
    ("german", "american", _RELATED),
]


def _build_lookup() -> dict[tuple[str, str], float]:
    table: dict[tuple[str, str], float] = {}
    for a, b, weight in _EDGES:
        # Keep the stronger weight if an edge is declared twice.
        table[(a, b)] = max(weight, table.get((a, b), 0.0))
        table[(b, a)] = max(weight, table.get((b, a), 0.0))
    return table


_LOOKUP = _build_lookup()

# The canonical cuisine vocabulary that actually carries adjacency signal —
# every node mentioned in an edge. Exposed so the eval simulator draws
# synthetic tastes from the same space the affinity map reasons over (a
# simulator using cuisines absent from the map would make affinity look
# useless for reasons unrelated to the ranker).
CANONICAL_CUISINES: tuple[str, ...] = tuple(sorted({node for edge in _EDGES for node in edge[:2]}))


def pair_affinity(user_cuisine: str, candidate_cuisine: str) -> float:
    """Adjacency weight between two canonical cuisines in [0, 1]."""
    if user_cuisine == candidate_cuisine:
        return 1.0
    return _LOOKUP.get((user_cuisine, candidate_cuisine), 0.0)


def affinity(weighted_cuisines: dict[str, float], candidate_cuisines: list[str]) -> float:
    """Best-matching affinity between a user's weighted tastes and a candidate.

    Uses the max over all (user cuisine, candidate cuisine) pairs rather than a
    sum, so a candidate tagged with many cuisines cannot inflate its own score
    by sheer breadth — it is judged by its single best match to the user.
    """
    if not weighted_cuisines or not candidate_cuisines:
        return 0.0
    best = 0.0
    for user_cuisine, weight in weighted_cuisines.items():
        for candidate_cuisine in candidate_cuisines:
            best = max(best, weight * pair_affinity(user_cuisine, candidate_cuisine))
    # Clamp the upper bound: weights are documented as [0, 1], but this is the
    # trust boundary — a malformed weight > 1 must not push the cuisine term
    # (and the composite score) out of range. Lower bound is 0 by construction.
    return min(1.0, best)
