-- Explicit grant posture (Supabase's standard model, pinned).
--
-- Two distinct layers, do not conflate them:
--   * GRANTs   = which roles may address a table at all (PostgREST exposure).
--   * RLS      = which ROWS a request may touch. The security boundary.
--
-- Supabase normally applies these grants via default privileges when
-- migrations run as `postgres`, but the local CLI stack can apply migrations
-- under a different role and silently skip them — the pgTAP suite caught
-- exactly that. Pinning the grants here makes local == hosted, always.
-- Broad grants are safe BECAUSE every table enables RLS at creation (D-012);
-- deny-all tables (sponsorships, reco_events, source_matches, reason_cache)
-- stay invisible to anon/authenticated regardless of these grants.

grant usage on schema public to anon, authenticated, service_role;

grant all on all tables in schema public to anon, authenticated, service_role;
grant all on all sequences in schema public to anon, authenticated, service_role;
grant all on all routines in schema public to anon, authenticated, service_role;

alter default privileges in schema public
  grant all on tables to anon, authenticated, service_role;
alter default privileges in schema public
  grant all on sequences to anon, authenticated, service_role;
alter default privileges in schema public
  grant all on routines to anon, authenticated, service_role;
