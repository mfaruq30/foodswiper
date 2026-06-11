-- Extensions required by the Munch schema.
-- PostGIS lives in the `extensions` schema per Supabase convention, so all
-- geography types below are referenced as extensions.geography.
create extension if not exists postgis with schema extensions;
