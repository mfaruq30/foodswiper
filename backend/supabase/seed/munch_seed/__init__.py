"""Munch open-data seed pipeline.

Stages (orchestrated by ``run.py``):

  download -> extract OSM POIs -> fetch inspections -> match -> curate -> load

Every venue row records its source + license (ODbL for OSM, PDDL / open terms
for city data) per spec §6.4. The pipeline is idempotent: restaurants upsert on
(osm_type, osm_id), vanished venues are tombstoned (is_active=false), and
match decisions persist in source_matches so re-runs cannot re-link history
(DECISIONS.md D-005/D-006).
"""
