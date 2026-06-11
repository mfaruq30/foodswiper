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


def seed_metro(metro: str, cache_dir: Path, out_dir: Path, db_url: str | None) -> int:
    """Run the full pipeline for one metro; returns the venue count."""
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

    if db_url:
        from .emit import load_direct

        load_direct(venues, match_rows, metro, run_started_at, db_url)
        print(f"[{metro}] loaded directly into Postgres")
    else:
        from .emit import write_sql_chunks

        paths = write_sql_chunks(venues, match_rows, metro, run_started_at, out_dir)
        print(f"[{metro}] wrote {len(paths)} SQL files to {out_dir}")
    return len(venues)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metro", choices=[*METRO_BOUNDS], action="append", dest="metros")
    parser.add_argument("--cache-dir", default=".seed_cache", type=Path)
    parser.add_argument("--out-dir", default="seed_out", type=Path)
    args = parser.parse_args(argv)

    metros = args.metros or list(METRO_BOUNDS)
    db_url = os.environ.get("SUPABASE_DB_URL") or None

    failed = False
    for metro in metros:
        count = seed_metro(metro, args.cache_dir, args.out_dir, db_url)
        if count < MIN_VENUES_PER_METRO:
            print(
                f"[{metro}] ERROR: only {count} venues (< {MIN_VENUES_PER_METRO}); "
                "a data source is likely broken",
                file=sys.stderr,
            )
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
