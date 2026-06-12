"""Layer 4 training (spec §7.5, D-008): LightGBM LambdaMART.

Separate from the serving code (app.learned_ranker) and from the eval harness
(evalharness) because it is the only part that needs LightGBM at all — the
`ml` optional extra. Train with `python -m learnedranker.train`, evaluate the
champion/challenger gate with `python -m learnedranker.evaluate`.

HONESTY (D-007): training on the synthetic harness validates the PLUMBING —
feature extraction, group structure, the LambdaMART objective, the promotion
gate — end to end. It is NOT evidence of real-world lift. The synthetic
labels come from a utility the ranker only partially observes (hidden `vibe`),
so a model that beats the heuristic here has learned to fit the OBSERVABLE
signal better than the hand weights, nothing more. Production promotion
requires logged swipes (≥50k / ≥5k mixed-label decks).
"""
