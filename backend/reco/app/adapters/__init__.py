"""Adapters: concrete implementations of the ports in app.ports.

memory    — ndjson-backed, in-process. The $0 demo path and the test fake.
firestore — the production backend (D-019, project food-5eb2a).

A future Postgres adapter slots in beside these without touching anything
above the ports (the migration seam promised in D-019).
"""
