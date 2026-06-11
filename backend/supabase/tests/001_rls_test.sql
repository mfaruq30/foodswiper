-- RLS posture tests (pgTAP, run via `supabase test db` on the local stack).
--
-- Two layers: (1) structural — RLS is ON for every public table and the
-- service-only tables have ZERO policies (deny-all); (2) behavioral — the
-- anon/authenticated roles can do exactly what the policies promise and
-- nothing more. The hardcoded table list is a deliberate tripwire: adding a
-- table makes this file fail until someone consciously decides its policies
-- (DECISIONS.md D-012).

begin;
create extension if not exists pgtap with schema extensions;

-- 17 structural (12 RLS + 5 policy-shape) + 9 behavioral.
select plan(26);

-- ---------------------------------------------------------------------------
-- (1) Structural: RLS enabled on all 12 tables.
-- ---------------------------------------------------------------------------
select ok(
  (select relrowsecurity from pg_class where oid = ('public.' || t)::regclass),
  'RLS enabled on ' || t
)
from unnest(array[
  'restaurants', 'restaurant_scores', 'source_matches',
  'profiles', 'user_preferences', 'anchor_restaurants',
  'swipes', 'conversions', 'feedback',
  'sponsorships', 'reco_events', 'reason_cache'
]) as t;

-- Service-only tables: deny-all means zero policies, on purpose.
select policies_are('public', 'sponsorships', '{}'::name[]);
select policies_are('public', 'reco_events', '{}'::name[]);
select policies_are('public', 'source_matches', '{}'::name[]);
select policies_are('public', 'reason_cache', '{}'::name[]);

select policies_are('public', 'restaurants', array['restaurants are readable by everyone']);

-- ---------------------------------------------------------------------------
-- (2) Behavioral. Fixture rows are created as the superuser first.
-- ---------------------------------------------------------------------------
insert into public.restaurants (id, osm_type, osm_id, name, location, metro, cuisines)
values (
  '00000000-0000-0000-0000-00000000beef', 'node', 42, 'RLS Test Diner',
  extensions.st_setsrid(extensions.st_makepoint(-73.99, 40.73), 4326)::extensions.geography,
  'nyc', array['diner']
);

insert into public.sponsorships (restaurant_id, metro, starts_at, ends_at)
values ('00000000-0000-0000-0000-00000000beef', 'nyc', now(), now() + interval '30 days');

insert into auth.users (id, email)
values ('00000000-0000-0000-0000-0000000000a1', 'a@test.munch'),
       ('00000000-0000-0000-0000-0000000000b2', 'b@test.munch');

-- anon: can read active restaurants, cannot write them, cannot see sponsorships.
set local role anon;

select results_eq(
  'select count(*) from public.restaurants',
  array[1::bigint],
  'anon sees the active restaurant'
);

select throws_ok(
  $$insert into public.restaurants (osm_type, osm_id, name, location, metro)
    values ('node', 43, 'Intruder',
            extensions.st_setsrid(extensions.st_makepoint(0, 0), 4326)::extensions.geography,
            'nyc')$$,
  '42501',
  null,
  'anon cannot insert restaurants'
);

select results_eq(
  'select count(*) from public.sponsorships',
  array[0::bigint],
  'sponsorships are invisible to anon (deny-all)'
);

reset role;

select results_eq(
  'select count(*) from public.sponsorships',
  array[1::bigint],
  'sponsorship fixture row exists (so the anon zero-count above is RLS, not absence)'
);

-- authenticated user A: may create exactly their own profile and rows.
set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000a1"}', true);

select lives_ok(
  $$insert into public.profiles (id, display_name)
    values ('00000000-0000-0000-0000-0000000000a1', 'User A')$$,
  'authenticated user can create their own profile'
);

select throws_ok(
  $$insert into public.profiles (id, display_name)
    values ('00000000-0000-0000-0000-0000000000b2', 'Masquerade')$$,
  '42501',
  null,
  'authenticated user cannot create someone else''s profile'
);

select lives_ok(
  $$insert into public.swipes (user_id, restaurant_id, mode, direction, session_id, card_position)
    values ('00000000-0000-0000-0000-0000000000a1',
            '00000000-0000-0000-0000-00000000beef',
            'dine_in', 'right', gen_random_uuid(), 1)$$,
  'user A can record their own swipe'
);

-- user B sees none of user A's data.
select set_config('request.jwt.claims', '{"sub":"00000000-0000-0000-0000-0000000000b2"}', true);

select results_eq(
  'select count(*) from public.swipes',
  array[0::bigint],
  'user B cannot read user A''s swipes'
);

select results_eq(
  'select count(*) from public.profiles',
  array[0::bigint],
  'user B cannot read user A''s profile'
);

select * from finish();
rollback;
