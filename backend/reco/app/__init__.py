"""Munch recommendation service.

Layered per spec §7: hard filters -> heuristic scorer -> learned ranker ->
reason generation, each independently testable. Phase 0 ships only the FastAPI
shell and health endpoint; ranking layers land in Phases 2 and 5.
"""
