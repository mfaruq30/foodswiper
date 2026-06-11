-- Restaurant inventory + Munch-owned signals + source-match audit trail.
--
-- ODbL hygiene (DECISIONS.md D-005 + DATA_MODEL.md): `restaurants` holds the
-- OSM ⋈ open-data merge and is treated as redistributable ODbL data, so it
-- carries NO proprietary columns. Munch-owned signals (swipe-derived scores)
-- live in `restaurant_scores`, keyed by id — a separate table by design, not
-- by accident. Do not "simplify" them back together.

create table public.restaurants (
  id uuid primary key default gen_random_uuid(),

  -- Stable identity in the source dataset; the seed pipeline upserts on this
  -- pair so weekly re-syncs can never duplicate or re-link a venue (D-006).
  osm_type text not null check (osm_type in ('node', 'way', 'relation')),
  osm_id bigint not null,

  name text not null,

  -- Canonicalized cuisine nodes (see seed pipeline cuisine map). Raw source
  -- tags are kept for audit because canonicalization is lossy and versioned.
  cuisines text[] not null default '{}',
  cuisines_raw text[] not null default '{}',

  -- OSM carries no price data at all (verified: 0 of 15,051 NYC POIs), so
  -- price is imputed in v1 and consumers must honor price_imputed (D-010).
  price_tier smallint check (price_tier between 1 and 4),
  price_imputed boolean not null default true,

  location extensions.geography(point, 4326) not null,
  metro public.metro not null,

  -- hours_known = false means "unknown", which PASSES the open-now filter
  -- with a UI badge — never hard-filter on unknown hours (D-010).
  hours jsonb,
  hours_known boolean not null default false,

  photo_urls text[] not null default '{}',
  dietary_tags text[] not null default '{}',
  address text,
  phone text,
  website text,

  source public.data_source not null default 'osm',
  -- License recorded per row (spec §6.4): ODbL-1.0 for OSM-derived rows,
  -- PDDL/open-terms identifiers for inspection-derived enrichment.
  source_license text not null default 'ODbL-1.0',
  -- Source-system identifiers (e.g. {"camis": "...", "boston_license": "..."}).
  external_ref jsonb not null default '{}',

  -- Cold-start quality prior from open data only (tag richness + inspection
  -- recency). The swipe-derived signal lives in restaurant_scores.
  popularity_prior real not null default 0,

  -- Tombstone, never delete: swipe/anchor history references these rows (D-006).
  is_active boolean not null default true,

  seeded_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  unique (osm_type, osm_id)
);

alter table public.restaurants enable row level security;

-- World-readable inventory, but only live rows; clients never see tombstones.
-- No insert/update/delete policies: writes go through the service role only.
create policy "restaurants are readable by everyone"
  on public.restaurants
  for select
  to anon, authenticated
  using (is_active);

create trigger restaurants_updated_at
  before update on public.restaurants
  for each row execute function public.set_updated_at();

create index restaurants_location_gist on public.restaurants using gist (location);
create index restaurants_metro_active on public.restaurants (metro) where is_active;
create index restaurants_cuisines_gin on public.restaurants using gin (cuisines);

-- Munch-owned, swipe-derived signal (Beta-smoothed in the reco service, D-009).
create table public.restaurant_scores (
  restaurant_id uuid primary key references public.restaurants (id) on delete cascade,
  impressions integer not null default 0,
  rights integer not null default 0,
  conversions integer not null default 0,
  -- Null until the restaurant has enough impressions for the posterior to
  -- mean anything; the UI hides the "N% liked this" line while null.
  internal_score real,
  updated_at timestamptz not null default now()
);

alter table public.restaurant_scores enable row level security;

create policy "scores are readable by everyone"
  on public.restaurant_scores
  for select
  to anon, authenticated
  using (true);

create trigger restaurant_scores_updated_at
  before update on public.restaurant_scores
  for each row execute function public.set_updated_at();

-- Persisted fuzzy-match decisions: OSM venue <-> inspection record (D-006).
-- Re-syncs consult this table so a match, once made (or manually corrected),
-- never silently flips and re-links swipe history to a different venue.
create table public.source_matches (
  id uuid primary key default gen_random_uuid(),
  osm_type text not null,
  osm_id bigint not null,
  inspection_source public.data_source not null,
  inspection_ref text not null,
  confidence real not null check (confidence between 0 and 1),
  decided_by public.match_decided_by not null default 'auto',
  created_at timestamptz not null default now(),
  unique (osm_type, osm_id, inspection_source)
);

-- RLS on, zero policies: service-role only. Internal pipeline state.
alter table public.source_matches enable row level security;
