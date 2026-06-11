"""Turn curated venues into idempotent SQL, and optionally load them directly.

Two delivery paths, same SQL semantics:
  * write_sql_chunks(): chunked .sql files (applied via the Supabase MCP/CLI
    when no database credential is available locally);
  * load_direct(): psycopg against SUPABASE_DB_URL (the CI re-sync path).

Idempotency contract (D-006): upsert on (osm_type, osm_id); after a full
metro run, rows not touched by it are tombstoned, never deleted.
"""

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from .records import Match, Venue


def _q(value: str | None) -> str:
    """SQL-quote a text value (standard '' escaping); NULL for None."""
    if value is None:
        return "null"
    return "'" + value.replace("'", "''") + "'"


def _text_array(values: list[str]) -> str:
    if not values:
        return "'{}'::text[]"
    return "array[" + ", ".join(_q(v) for v in values) + "]::text[]"


def _hours_json(hours_raw: str | None) -> str:
    # Raw opening_hours string preserved as jsonb; structured parsing is the
    # Phase 2 open-now filter's job (FUTURE(Phase 2), D-010).
    if hours_raw is None:
        return "null"
    return _q(json.dumps({"raw": hours_raw})) + "::jsonb"


def venue_row(v: Venue) -> str:
    """One VALUES tuple for the restaurants upsert."""
    point = (
        f"extensions.st_setsrid(extensions.st_makepoint({v.lon:.7f}, {v.lat:.7f}), 4326)"
        "::extensions.geography"
    )
    return (
        "("
        f"{_q(v.osm_type)}, {v.osm_id}, {_q(v.name)}, "
        f"{_text_array(v.cuisines)}, {_text_array(v.cuisines_raw)}, "
        f"{v.price_tier}, true, "  # price always imputed in v1 (D-010)
        f"{point}, {_q(v.metro)}::public.metro, "
        f"{_hours_json(v.hours_raw)}, {str(bool(v.hours_raw)).lower()}, "
        f"{_q(v.phone)}, {_q(v.website)}, {_q(v.address)}, "
        f"{_text_array(v.dietary_tags)}, "
        f"'osm'::public.data_source, {_q(v.source_license)}, "
        f"{_q(json.dumps(v.external_ref))}::jsonb, "
        f"{v.popularity_prior}"
        ")"
    )


_VENUE_COLUMNS = (
    "osm_type, osm_id, name, cuisines, cuisines_raw, price_tier, price_imputed, "
    "location, metro, hours, hours_known, phone, website, address, dietary_tags, "
    "source, source_license, external_ref, popularity_prior"
)

# updated_at is set explicitly (not left to the trigger) so the tombstone
# step can use "updated_at < run start" as its untouched-row predicate.
_VENUE_UPSERT_FOOTER = """
on conflict (osm_type, osm_id) do update set
  name = excluded.name,
  cuisines = excluded.cuisines,
  cuisines_raw = excluded.cuisines_raw,
  price_tier = excluded.price_tier,
  location = excluded.location,
  metro = excluded.metro,
  hours = excluded.hours,
  hours_known = excluded.hours_known,
  phone = excluded.phone,
  website = excluded.website,
  address = excluded.address,
  dietary_tags = excluded.dietary_tags,
  source_license = excluded.source_license,
  external_ref = excluded.external_ref,
  popularity_prior = excluded.popularity_prior,
  is_active = true,
  updated_at = now();
"""


def venue_upsert_sql(venues: Iterable[Venue]) -> str:
    rows = ",\n".join(venue_row(v) for v in venues)
    header = f"insert into public.restaurants ({_VENUE_COLUMNS})\nvalues\n"
    return f"{header}{rows}{_VENUE_UPSERT_FOOTER}"


def scores_init_sql() -> str:
    """Ensure every restaurant has a scores row (zeroed; D-009 smoothing is
    computed in the reco service, not here)."""
    return (
        "insert into public.restaurant_scores (restaurant_id)\n"
        "select id from public.restaurants\n"
        "on conflict (restaurant_id) do nothing;"
    )


def match_upsert_sql(matches: Iterable[Match]) -> str:
    rows = ",\n".join(
        f"({_q(m.osm_type)}, {m.osm_id}, {_q(m.inspection_source)}::public.data_source, "
        f"{_q(m.inspection_ref)}, {m.confidence})"
        for m in matches
    )
    # do nothing on conflict: an existing decision (possibly manual) wins —
    # re-runs must never flip a match (D-006).
    return (
        "insert into public.source_matches "
        "(osm_type, osm_id, inspection_source, inspection_ref, confidence)\n"
        f"values\n{rows}\n"
        "on conflict (osm_type, osm_id, inspection_source) do nothing;"
    )


def tombstone_sql(metro: str, run_started_at_iso: str) -> str:
    """Soft-close venues the just-finished metro run did not touch.

    source <> 'user' guard: user-submitted venues (post-launch) are not in the
    open-data sync's jurisdiction and must never be auto-closed by it.
    """
    return (
        "update public.restaurants set is_active = false, updated_at = now()\n"
        f"where metro = {_q(metro)}::public.metro\n"
        f"  and source <> 'user'::public.data_source\n"
        f"  and updated_at < {_q(run_started_at_iso)};"
    )


def _chunks[T](items: list[T], size: int) -> Iterator[list[T]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def write_sql_chunks(
    venues: list[Venue],
    matches: list[Match],
    metro: str,
    run_started_at_iso: str,
    out_dir: Path,
    chunk_size: int = 200,
) -> list[Path]:
    """Write the full load as ordered .sql files; returns the written paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    def write(name: str, sql: str) -> None:
        path = out_dir / name
        path.write_text(sql, encoding="utf-8", newline="\n")
        paths.append(path)

    for i, venue_chunk in enumerate(_chunks(venues, chunk_size)):
        write(f"{metro}_10_venues_{i:03d}.sql", venue_upsert_sql(venue_chunk))
    if matches:
        for i, match_chunk in enumerate(_chunks(matches, chunk_size * 2)):
            write(f"{metro}_20_matches_{i:03d}.sql", match_upsert_sql(match_chunk))
    write(f"{metro}_30_scores.sql", scores_init_sql())
    write(f"{metro}_40_tombstone.sql", tombstone_sql(metro, run_started_at_iso))
    return paths


def load_direct(
    venues: list[Venue],
    matches: list[Match],
    metro: str,
    run_started_at_iso: str,
    db_url: str,
    chunk_size: int = 500,
) -> None:
    """Apply the same statements over a direct Postgres connection."""
    import psycopg  # imported lazily: the SQL-file path needs no driver

    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            for venue_chunk in _chunks(venues, chunk_size):
                cur.execute(venue_upsert_sql(venue_chunk))
            for match_chunk in _chunks(matches, chunk_size):
                cur.execute(match_upsert_sql(match_chunk))
            cur.execute(scores_init_sql())
            cur.execute(tombstone_sql(metro, run_started_at_iso))
        conn.commit()
