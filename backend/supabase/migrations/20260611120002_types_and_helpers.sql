-- Shared enum types + trigger helpers.
--
-- Why enums over text + CHECK: these values are wire contracts shared with
-- the iOS client (MunchKit mirrors them, e.g. Metro) and the reco service;
-- an enum makes an invalid value a type error at the database boundary.

create type public.metro as enum ('nyc', 'boston');

create type public.data_source as enum ('osm', 'nyc_open_data', 'boston_open_data', 'user');

create type public.swipe_mode as enum ('dine_in', 'pickup', 'delivery');

create type public.swipe_direction as enum ('left', 'right');

create type public.anchor_source as enum ('onboarding', 'conversion');

create type public.match_decided_by as enum ('auto', 'manual');

-- Conversion = an outbound tap, logged honestly as such (DECISIONS.md D-010):
-- we cannot observe a completed order through a deep link.
create type public.conversion_type as enum
  ('directions', 'call', 'reserve', 'order_pickup', 'order_delivery');

-- Generic updated_at maintenance. SECURITY: search_path pinned empty so the
-- trigger cannot be hijacked via schema shadowing (Supabase advisor lint).
create function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;
