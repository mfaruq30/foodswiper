"""Offline evaluation harness (spec §7.4) — implemented in Phase 2.

Scaffolded before any learned ranker exists on purpose: you cannot improve
what you cannot measure. Phase 2 adds the synthetic user simulator, the
ranking metrics (Precision@k, Recall@k, NDCG@k, MRR, hit-rate@k), and the
champion/challenger regression guard.

Honesty contract for this harness (docs/DECISIONS.md D-007): results on
synthetic data validate the PLUMBING — metric code, group structure, training
pipeline, promotion gate — they are not evidence of real-world ranking lift.
"""
