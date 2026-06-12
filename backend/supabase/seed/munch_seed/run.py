"""Seed pipeline orchestrator: ``python -m munch_seed.run [--metro nyc|boston]``.

Stages: download PBF (cached) -> extract OSM POIs -> fetch inspections ->
match -> curate -> emit (SQL files) or load (SUPABASE_DB_URL). Prints a
summary per metro; exits non-zero if any metro produced fewer than 500 venues
(the spec §6.4 floor), so a quietly broken source fails the run loudly.
"""

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

from .config import GEOFABRIK_URLS, METRO_BOUNDS, TARGET_PER_METRO
from .curate import curate
from .inspections import fetch_boston, fetch_nyc
from .matching import match_pois
from .osm_extract import extract_pois

# The spec's lower bound; below this the metro's data path is broken.
MIN_VENUES_PER_METRO = 500

# Both cities publish thousands of establishment records; near-zero always
# means the fetcher broke (e.g. a renamed field dropping every row — which
# happened on the first real Boston run), never that the city emptied out.
MIN_INSPECTION_RECORDS = 100


def _download_pbf(metro: str, cache_dir: Path) -> Path:
    """Fetch the Geofabrik extract unless a cached copy exists.

    Cache-by-filename is deliberate: extracts update daily but a same-day
    re-run should not re-download 300-470 MB. The weekly CI run starts with
    an empty cache, so freshness is bounded by the cron cadence (D-006).
    """
    url = GEOFABRIK_URLS[metro]
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / url.rsplit("/", 1)[1]
    if target.exists() and target.stat().st_size > 0:
        print(f"[{metro}] using cached {target.name}")
        return target
    print(f"[{metro}] downloading {url}")
    with httpx.Client(timeout=httpx.Timeout(120.0), follow_redirects=True) as client:  # noqa: SIM117
        with client.stream("GET", url) as response:
            response.raise_for_status()
            tmp = target.with_suffix(".part")
            with tmp.open("wb") as fh:
                for chunk in response.iter_bytes(1 << 20):
                    fh.write(chunk)
            tmp.replace(target)
    print(f"[{metro}] downloaded {target.stat().st_size / 1e6:.0f} MB")
    return target


def seed_metro(
    metro: str, cache_dir: Path, out_dir: Path, ndjson_path: Path, db_url: str | None
) -> tuple[int, int]:
    """Run the full pipeline for one metro; returns (venues, inspection records)."""
    run_started_at = datetime.now(UTC).isoformat()

    pbf = _download_pbf(metro, cache_dir)
    pois = extract_pois(str(pbf), METRO_BOUNDS[metro])
    print(f"[{metro}] OSM POIs in bbox: {len(pois)}")

    inspections = fetch_nyc() if metro == "nyc" else fetch_boston()
    print(f"[{metro}] inspection/license records: {len(inspections)}")

    matches = match_pois(pois, inspections)
    print(f"[{metro}] matched POIs: {len(matches)} ({len(matches) * 100 // max(len(pois), 1)}%)")

    venues = curate(pois, matches, metro, datetime.now(UTC), target=TARGET_PER_METRO)
    match_rows = [
        matches[(v.osm_type, v.osm_id)][0] for v in venues if (v.osm_type, v.osm_id) in matches
    ]
    print(f"[{metro}] curated venues: {len(venues)} (matched: {len(match_rows)})")

    # The canonical, backend-neutral artifact every writer consumes (D-019);
    # main() owns the .part-then-promote lifecycle of the path passed in.
    from .canonical import append_ndjson

    append_ndjson(venues, ndjson_path)
    print(f"[{metro}] appended {len(venues)} records to {ndjson_path}")

    if db_url:
        from .emit import load_direct

        load_direct(venues, match_rows, metro, run_started_at, db_url)
        print(f"[{metro}] loaded directly into Postgres")
    else:
        from .emit import write_sql_chunks

        paths = write_sql_chunks(venues, match_rows, metro, run_started_at, out_dir)
        print(f"[{metro}] wrote {len(paths)} SQL files to {out_dir}")
    return len(venues), len(inspections)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metro", choices=[*METRO_BOUNDS], action="append", dest="metros")
    parser.add_argument("--cache-dir", default=".seed_cache", type=Path)
    parser.add_argument("--out-dir", default="seed_out", type=Path)
    parser.add_argument(
        "--load-firestore",
        metavar="PROJECT_ID",
        help="after the run, upsert venues.ndjson into this Firebase project (D-019)",
    )
    args = parser.parse_args(argv)

    if args.load_firestore:
        # Fail fast: the firestore extra is optional, and discovering it is
        # missing AFTER a 300-470 MB download + extraction would burn the run.
        import importlib.util

        if importlib.util.find_spec("google.cloud.firestore") is None:
            parser.error("--load-firestore requires: uv pip install -e .[firestore]")

    metros = args.metros or list(METRO_BOUNDS)
    db_url = os.environ.get("SUPABASE_DB_URL") or None

    # The canonical artifact builds under a .part name and is renamed only
    # after every metro passes its floors — a crashed or floor-failed run can
    # never leave a coherent-looking half-artifact at the canonical path.
    ndjson_path = args.out_dir / "venues.ndjson"
    part_path = args.out_dir / "venues.ndjson.part"
    if part_path.exists():
        part_path.unlink()

    failed = False
    for metro in metros:
        venues, inspections = seed_metro(metro, args.cache_dir, args.out_dir, part_path, db_url)
        if venues < MIN_VENUES_PER_METRO:
            print(
                f"[{metro}] ERROR: only {venues} venues (< {MIN_VENUES_PER_METRO}); "
                "a data source is likely broken",
                file=sys.stderr,
            )
            failed = True
        if inspections < MIN_INSPECTION_RECORDS:
            print(
                f"[{metro}] ERROR: only {inspections} inspection records "
                f"(< {MIN_INSPECTION_RECORDS}); the city fetcher is broken — venues "
                "were emitted without enrichment, review before loading",
                file=sys.stderr,
            )
            failed = True

    if failed:
        print(f"[artifact] left at {part_path} (floors failed; not promoted)", file=sys.stderr)
        if args.load_firestore:
            print("[firestore] SKIPPED: not loading bad data", file=sys.stderr)
        return 1

    part_path.replace(ndjson_path)
    print(f"[artifact] promoted {ndjson_path}")

    if args.load_firestore:
        from .firestore_writer import load_ndjson_to_firestore

        upserted, tombstoned = load_ndjson_to_firestore(ndjson_path, args.load_firestore)
        print(f"[firestore] upserted {upserted}, tombstoned {tombstoned} ({args.load_firestore})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
