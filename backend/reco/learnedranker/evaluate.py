"""Champion/challenger gate: ``python -m learnedranker.evaluate``.

Evaluates the trained challenger against the heuristic champion on a FRESH
synthetic split (a different seed from training — no leakage), prints the
bracket, writes it to docs/ALGORITHM.md, and gates:

  challenger NDCG@5 >= champion NDCG@5 + margin  ->  exit 0 (validated)

HONESTY (D-007): passing this gate validates the PLUMBING — the model trains,
the feature contract round-trips, the challenger fits the OBSERVABLE signal
better than the hand weights. It is NOT clearance to ship the learned ranker
to users. The heuristic stays the production champion until the gate is run
on LOGGED SWIPES, not synthetic decks.
"""

from __future__ import annotations

import argparse
import random
import sys
from collections.abc import Callable
from pathlib import Path

from app.learned_ranker import load_learned_ranker
from evalharness.run import (
    _heuristic_ranker,
    _oracle_ranker,
    _random_ranker,
    evaluate,
)
from evalharness.simulator import EvalInstance, build_instance, generate_users, generate_world

from .train import DEFAULT_MODEL_PATH

# Different from train's default seed: evaluate on decks the model never saw.
DEFAULT_EVAL_SEED = 4242
GATE_MARGIN = 0.005  # challenger must clear the champion by this NDCG@5 margin

_LEARNED_START = "<!-- LEARNED:START -->"
_LEARNED_END = "<!-- LEARNED:END -->"


def _learned_ranker(model_path: Path) -> Callable[[EvalInstance], list[str]] | None:
    ranker = load_learned_ranker(model_path)
    if ranker is None:
        return None

    def rank(instance: EvalInstance) -> list[str]:
        ordered = ranker.rank(instance.profile, instance.context, instance.candidates)
        return [r.id for r in ordered]

    return rank


def _build_instances(seed: int, users: int, venues: int) -> list[EvalInstance]:
    rng = random.Random(seed)
    world = generate_world(rng, venues)
    user_list = generate_users(rng, users)
    return [build_instance(rng, u, world, 40) for u in user_list]


def _write_doc(table: str) -> None:
    doc = Path(__file__).resolve().parents[3] / "docs" / "ALGORITHM.md"
    if not doc.exists():
        return
    text = doc.read_text(encoding="utf-8")
    if _LEARNED_START not in text or _LEARNED_END not in text:
        return
    block = f"{_LEARNED_START}\n{table}\n{_LEARNED_END}"
    before = text.split(_LEARNED_START)[0]
    after = text.split(_LEARNED_END)[1]
    doc.write_text(before + block + after, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_EVAL_SEED)
    parser.add_argument("--users", type=int, default=600)
    parser.add_argument("--venues", type=int, default=400)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    args = parser.parse_args(argv)

    learned = _learned_ranker(args.model_path)
    if learned is None:
        print(
            f"GATE SKIPPED: no usable model at {args.model_path} (train first, "
            "and install the `ml` extra)",
            file=sys.stderr,
        )
        return 2

    instances = _build_instances(args.seed, args.users, args.venues)
    results = {
        "random": evaluate(_random_ranker(args.seed), instances),
        "heuristic": evaluate(_heuristic_ranker(), instances),
        "learned": evaluate(learned, instances),
        "oracle": evaluate(_oracle_ranker(), instances),
    }

    header = "| Ranker | NDCG@1 | NDCG@3 | NDCG@5 | P@5 | MRR |"
    sep = "|---|---|---|---|---|---|"
    rows = [
        "_Synthetic held-out eval (D-007: plumbing validation, NOT real lift). "
        "The learned challenger only fits the OBSERVABLE signal better than the "
        "hand weights; the heuristic stays production champion until this gate "
        "runs on logged swipes._",
        "",
        header,
        sep,
    ]
    for name in ("random", "heuristic", "learned", "oracle"):
        m = results[name]
        rows.append(
            f"| {name} | {m['ndcg@1']:.3f} | {m['ndcg@3']:.3f} | {m['ndcg@5']:.3f} "
            f"| {m['p@5']:.3f} | {m['mrr']:.3f} |"
        )
    table = "\n".join(rows)
    print(table)
    _write_doc(table)

    champion = results["heuristic"]["ndcg@5"]
    challenger = results["learned"]["ndcg@5"]
    ceiling = results["oracle"]["ndcg@5"]
    print(
        f"\nNDCG@5 — champion(heuristic)={champion:.3f}  challenger(learned)={challenger:.3f}  "
        f"ceiling(oracle)={ceiling:.3f}"
    )
    # Sanity: the challenger must also stay under the oracle, or the simulator
    # stopped hiding signal (the whole bracket would be circular — D-020).
    if challenger >= ceiling:
        print("GATE FAILED: learned reached the oracle — grading is circular", file=sys.stderr)
        return 1
    if challenger < champion + GATE_MARGIN:
        print(
            f"GATE FAILED: challenger {challenger:.3f} did not beat champion "
            f"{champion:.3f} by {GATE_MARGIN} on synthetic plumbing",
            file=sys.stderr,
        )
        return 1
    print("GATE PASSED (synthetic plumbing): random < heuristic < learned < oracle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
