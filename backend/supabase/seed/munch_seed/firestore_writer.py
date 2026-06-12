"""Load the canonical venues.ndjson into Firestore (project food-5eb2a).

The ONLY backend-specific writer in the pipeline (D-019): reads the neutral
ndjson, adds the two Firestore-only derived fields (geohash for radius
queries, name_lower for prefix autocomplete), and upserts. A future Postgres
writer reads the same ndjson and emits SQL instead — the seam in action.

Idempotency mirrors D-006: doc id = the canonical venue id, upserts by id,
vanished venues are tombstoned (is_active=false) never deleted, and
venue_scores docs are created once and never overwritten (they hold
Munch-owned swipe counters the sync must not reset).

Credentials: Application Default Credentials (a service-account key via
GOOGLE_APPLICATION_CREDENTIALS, or `gcloud auth application-default login`),
or the emulator via FIRESTORE_EMULATOR_HOST — see RUNBOOK.md.
"""

import json
from pathlib import Path
from typing import Any

from .geohash import encode

_BATCH_LIMIT = 450  # Firestore caps batches at 500 ops; headroom for safety.


def _doc(record: dict[str, Any]) -> dict[str, Any]:
    """ndjson record -> venue document (adds the derived query fields)."""
    doc = dict(record)
    doc.pop("id")
    doc["geohash"] = encode(float(record["lat"]), float(record["lon"]))
    doc["name_lower"] = str(record["name"]).lower()
    doc["is_active"] = True
    return doc


def load_ndjson_to_firestore(ndjson_path: Path, project_id: str) -> tuple[int, int]:
    """Upsert all venues; tombstone strays. Returns (upserted, tombstoned).

    The tombstone pass is scoped to the metros PRESENT IN THE ARTIFACT — never
    the whole collection. Without that scope, loading a single-metro artifact
    would tombstone every venue of the other metro (caught in the Phase 3
    review before it could fire in production).
    """
    from google.cloud import firestore

    client = firestore.Client(project=project_id)
    with ndjson_path.open(encoding="utf-8") as fh:
        records = [json.loads(line) for line in fh if line.strip()]

    # One upfront listing instead of a per-venue point read (document ids via
    # list_documents are not billed as reads).
    existing_scores = {ref.id for ref in client.collection("venue_scores").list_documents()}

    seen_ids = set()
    artifact_metros: set[str] = set()
    batch = client.batch()
    pending = 0
    for record in records:
        venue_id = str(record["id"])
        seen_ids.add(venue_id)
        artifact_metros.add(str(record["metro"]))
        batch.set(client.collection("venues").document(venue_id), _doc(record))
        pending += 1
        if venue_id not in existing_scores:
            # Create-once only — never reset Munch-owned swipe counters.
            scores_ref = client.collection("venue_scores").document(venue_id)
            batch.set(scores_ref, {"impressions": 0, "rights": 0, "internal_score": None})
            pending += 1
        if pending >= _BATCH_LIMIT:
            batch.commit()
            batch = client.batch()
            pending = 0
    if pending:
        batch.commit()

    # Tombstone venues that vanished from the canonical set (D-006 semantics),
    # scoped to the metros this artifact actually covers.
    tombstoned = 0
    tombstone_batch = client.batch()
    tombstone_pending = 0
    query = (
        client.collection("venues")
        .where("is_active", "==", True)
        .where("metro", "in", sorted(artifact_metros))
    )
    for snap in query.stream():
        if snap.id not in seen_ids:
            tombstone_batch.update(snap.reference, {"is_active": False})
            tombstoned += 1
            tombstone_pending += 1
            if tombstone_pending >= _BATCH_LIMIT:
                tombstone_batch.commit()
                tombstone_batch = client.batch()
                tombstone_pending = 0
    if tombstone_pending:
        tombstone_batch.commit()
    return len(records), tombstoned
