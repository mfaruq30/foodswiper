# Munch — Runbook

> Phase 0 skeleton. Each section is filled in the phase that makes it real;
> placeholders say so explicitly rather than pretending.

## Deploy

- **Reco service (Cloud Run):** _Phase 3._ `gcloud run deploy` from
  `backend/reco/Dockerfile`; min-instances 0 (free tier), env vars from
  Secret Manager.
- **Edge functions:** _Phase 3._ `supabase functions deploy <name>`.
- **Migrations:** _Phase 1._ `supabase db push` (CI) / `supabase migration up`
  (local stack).
- **iOS (TestFlight):** _Phase 6._ CI archive on `macos-26` + App Store
  Connect API key upload via fastlane. No human Mac in the loop.

## Secrets

All secrets are environment-side (`.env.example` is the catalog; the repo
never holds a real value).

- **Anthropic key:** create ONLY after setting a monthly spend cap in the
  Anthropic Console (D-004). Rotate: issue new key → update Cloud Run secret →
  revoke old. The app must keep working with the key absent (templated reasons).
- **Supabase service-role key:** GitHub Actions secret for the re-sync
  workflow only. Never in client code.
- **Apple SIWA .p8 key:** Supabase edge-function secret, used by
  `delete-account` for TN3194 token revocation (D-013).

## Seed / re-sync a city

_Phase 1._ `make seed` locally; weekly `resync.yml` in CI. Safety rails
(already encoded in the workflow comments): pg_dump artifact before writes,
idempotent upserts, tombstones not deletes, persisted match decisions,
keepalive against the 7-day free-tier pause (D-006).

## Known operational landmines (verified at kickoff)

1. Supabase free tier pauses projects after 7 idle days — keepalive lives in
   the resync workflow.
2. Free tier has NO automatic backups — the pre-sync pg_dump artifact is the
   backup.
3. macOS CI minutes: ~200/month real — keep `ios-build.yml` path-filtered;
   never trigger it from backend changes.
4. Local Supabase stack + pgTAP requires Docker Desktop — **not currently
   installed on the dev machine**; install before Phase 1 RLS testing.
