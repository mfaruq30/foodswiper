-- User identity and taste-profile tables. All user rows are owner-scoped via
-- RLS; the service role (edge functions, reco service) bypasses RLS by design.

create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  dietary_flags jsonb not null default '{}',
  home_metro public.metro,

  -- Apple SIWA refresh token, stored (encrypted by the auth edge function)
  -- from the FIRST sign-in: Apple TN3194 requires token revocation on account
  -- deletion, and a token never stored can never be revoked (D-013).
  apple_refresh_token text,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "users read own profile"
  on public.profiles for select
  to authenticated
  using ((select auth.uid()) = id);

create policy "users create own profile"
  on public.profiles for insert
  to authenticated
  with check ((select auth.uid()) = id);

create policy "users update own profile"
  on public.profiles for update
  to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

-- No delete policy: deletion happens only through the delete-account edge
-- function (service role), which also purges auth.users and revokes the
-- Apple token — a client-side row delete would skip both.

create trigger profiles_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

create table public.user_preferences (
  user_id uuid not null references public.profiles (id) on delete cascade,
  mode public.swipe_mode not null,
  cuisine_weights jsonb not null default '{}',
  price_pref smallint check (price_pref between 1 and 4),
  ambiance_pref jsonb not null default '{}',
  updated_at timestamptz not null default now(),
  primary key (user_id, mode)
);

alter table public.user_preferences enable row level security;

create policy "users manage own preferences"
  on public.user_preferences for all
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create trigger user_preferences_updated_at
  before update on public.user_preferences
  for each row execute function public.set_updated_at();

-- Anchor restaurants: the cold-start signal (spec §7.3). `on delete restrict`
-- on the restaurant side is deliberate — venues are tombstoned, never deleted,
-- and a hard delete that would orphan anchors should fail loudly.
create table public.anchor_restaurants (
  user_id uuid not null references public.profiles (id) on delete cascade,
  restaurant_id uuid not null references public.restaurants (id) on delete restrict,
  source public.anchor_source not null default 'onboarding',
  created_at timestamptz not null default now(),
  primary key (user_id, restaurant_id)
);

alter table public.anchor_restaurants enable row level security;

create policy "users manage own anchors"
  on public.anchor_restaurants for all
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create index anchor_restaurants_restaurant_idx
  on public.anchor_restaurants (restaurant_id);
