-- Behavioral event log + serving infrastructure tables.
--
-- swipes/conversions are append-only from the client (insert + select-own,
-- no update/delete policies): they are the training data, and a mutable
-- training log is a silent-corruption hazard.

create table public.swipes (
  id bigint generated always as identity primary key,
  user_id uuid not null references public.profiles (id) on delete cascade,
  restaurant_id uuid not null references public.restaurants (id) on delete restrict,
  mode public.swipe_mode not null,
  direction public.swipe_direction not null,
  session_id uuid not null,

  -- Position of the card within its served deck and whether it occupied an
  -- exploration slot — both required for unbiased Layer-4 training (D-008/D-009).
  card_position smallint not null,
  explore boolean not null default false,

  -- Serving context (time bucket, party size, weather...) — jsonb because the
  -- feature set will evolve faster than we want schema migrations.
  context jsonb not null default '{}',
  created_at timestamptz not null default now()
);

alter table public.swipes enable row level security;

create policy "users insert own swipes"
  on public.swipes for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

create policy "users read own swipes"
  on public.swipes for select
  to authenticated
  using ((select auth.uid()) = user_id);

create index swipes_user_created_idx on public.swipes (user_id, created_at);
create index swipes_restaurant_idx on public.swipes (restaurant_id);
create index swipes_created_idx on public.swipes (created_at);

create table public.conversions (
  id bigint generated always as identity primary key,
  user_id uuid not null references public.profiles (id) on delete cascade,
  restaurant_id uuid not null references public.restaurants (id) on delete restrict,
  mode public.swipe_mode not null,
  conversion_type public.conversion_type not null,
  created_at timestamptz not null default now()
);

alter table public.conversions enable row level security;

create policy "users insert own conversions"
  on public.conversions for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

create policy "users read own conversions"
  on public.conversions for select
  to authenticated
  using ((select auth.uid()) = user_id);

create index conversions_user_idx on public.conversions (user_id, created_at);
create index conversions_restaurant_idx on public.conversions (restaurant_id);

create table public.feedback (
  user_id uuid not null references public.profiles (id) on delete cascade,
  restaurant_id uuid not null references public.restaurants (id) on delete restrict,
  rating smallint not null check (rating in (-1, 0, 1)),
  source text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, restaurant_id)
);

alter table public.feedback enable row level security;

create policy "users manage own feedback"
  on public.feedback for all
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create trigger feedback_updated_at
  before update on public.feedback
  for each row execute function public.set_updated_at();

create index feedback_restaurant_idx on public.feedback (restaurant_id);

-- Sponsorship rules (no admin UI in v1 — spec §15). THE canonical RLS trap
-- (D-012): a dormant table nothing exercises. RLS on, zero policies; only the
-- service role (get-deck insertion logic, future sales tooling) touches it.
create table public.sponsorships (
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references public.restaurants (id) on delete restrict,
  metro public.metro not null,
  monthly_fee numeric(10, 2),
  match_criteria jsonb not null default '{}',
  max_impressions_per_day integer,
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  created_at timestamptz not null default now(),
  check (ends_at > starts_at)
);

alter table public.sponsorships enable row level security;

create index sponsorships_restaurant_idx on public.sponsorships (restaurant_id);
create index sponsorships_metro_window_idx on public.sponsorships (metro, starts_at, ends_at);

-- Every served deck — THE training/eval log (spec §5). Written exclusively by
-- the get-deck edge function (service role); user_id cascades on account
-- deletion because the privacy policy promises full purge (D-013).
create table public.reco_events (
  id bigint generated always as identity primary key,
  request_id uuid not null,
  user_id uuid references public.profiles (id) on delete cascade,
  mode public.swipe_mode not null,
  candidate_ids jsonb not null,
  served_order jsonb not null,
  model_version text not null,
  latency_ms integer,
  created_at timestamptz not null default now()
);

alter table public.reco_events enable row level security;

create index reco_events_user_idx on public.reco_events (user_id);
create index reco_events_created_idx on public.reco_events (created_at);

-- Pre-generated reason text, keyed by (restaurant, taste-archetype, mode) —
-- the LLM is off the serve path (D-004). Service-role only: reasons reach the
-- client inside get-deck responses, never via direct table reads.
create table public.reason_cache (
  restaurant_id uuid not null references public.restaurants (id) on delete cascade,
  archetype text not null,
  mode public.swipe_mode not null,
  reason text not null,
  model_version text not null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  primary key (restaurant_id, archetype, mode)
);

alter table public.reason_cache enable row level security;
