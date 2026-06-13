# Munch — Runbook

> Phase 0 skeleton. Each section is filled in the phase that makes it real;
> placeholders say so explicitly rather than pretending.

## Firebase (project food-5eb2a, D-019)

- **Credentials for seeding/admin:** either set `GOOGLE_APPLICATION_CREDENTIALS`
  to a service-account key JSON (Firebase console → Project settings → Service
  accounts → Generate new private key) or run
  `npx firebase-tools login` + `gcloud auth application-default login`.
  Never commit the key; it is the root password.
- **Load venues:** `uv run -- python -m munch_seed.run --load-firestore food-5eb2a`
  (re-uses cached extracts; consumes `seed_out/venues.ndjson`).
- **Deploy rules + indexes:** `npx firebase-tools deploy --only firestore --project food-5eb2a`.
- **Emulator (needs Java, installed):** `npx firebase-tools emulators:start`;
  point the API at it with `FIRESTORE_EMULATOR_HOST=localhost:8089`.
- **Run the API locally, $0 demo mode (no Firebase at all):**
  `MUNCH_BACKEND=memory MUNCH_AUTH=dev VENUES_NDJSON=<path> uvicorn app.main:app`
  — dev auth treats the bearer token as the uid; never enable outside demos.

## Hosted legal site (GitHub Pages)

- **Source:** `web/` (plain HTML, `.nojekyll`), deployed by
  `.github/workflows/pages.yml` on push to `main` touching `web/**`.
- **One-time enable:** Settings → Pages → Source: **GitHub Actions** (repo is
  github.com/mfaruq30/foodswiper). The workflow runs but won't publish until
  this is set.
- **URL pattern:** `https://mfaruq30.github.io/foodswiper/`.
- **App Store Connect Privacy Policy URL:**
  `https://mfaruq30.github.io/foodswiper/privacy.html`.
- Other pages: `/terms.html`, `/support.html`, `/data-sources.html` (the ODbL
  © OpenStreetMap contributors attribution page).

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
- **Apple SIWA .p8 key + team/key/service ids:** reco-service env, read by
  `apple_auth.py` to mint the ES256 client secret and revoke the user's refresh
  token on account deletion (TN3194, D-013). Set the four `APPLE_*` vars in
  Cloud Run (provide the .p8 via `APPLE_PRIVATE_KEY` from Secret Manager, or
  `APPLE_PRIVATE_KEY_PATH`). All absent = no revoke, deletion still purges data.
  Full setup + rotation: `docs/RELEASE.md`.

## Seed / re-sync a city

```sh
cd backend/supabase/seed
uv run -- python -m munch_seed.run                 # both metros
uv run -- python -m munch_seed.run --metro boston  # one metro
```

Without `SUPABASE_DB_URL` set, the run writes ordered SQL chunks to
`seed_out/` (apply via the Supabase MCP or `psql`); with it, it loads
directly. Downloads cache in `.seed_cache/` (~760 MB for both extracts).
The run fails non-zero if any metro yields < 500 venues — that means a
source broke, not that the city shrank.

Safety rails encoded in the pipeline + resync.yml: idempotent upserts on
(osm_type, osm_id); tombstones (`is_active=false`) never deletes; the
tombstone step never touches `source='user'` rows; match decisions persist in
`source_matches` (manual corrections win over re-runs); pg_dump artifact
before CI writes; keepalive against the 7-day free-tier pause (D-006).

## Database tests (RLS)

pgTAP suite: [backend/supabase/tests/001_rls_test.sql](../backend/supabase/tests/001_rls_test.sql).
Requires Docker (not on the dev machine — runs in the `db-tests` CI lane):

```sh
cd backend
supabase db start   # local Postgres + migrations
supabase test db    # pg_prove over supabase/tests/*.sql
```

Adding a table without updating the RLS test fails the suite — that is the
tripwire working (D-012), not a flaky test.

## Known operational landmines (verified at kickoff)

1. Supabase free tier pauses projects after 7 idle days — keepalive lives in
   the resync workflow.
2. Free tier has NO automatic backups — the pre-sync pg_dump artifact is the
   backup.
3. macOS CI minutes: ~200/month real — keep `ios-build.yml` path-filtered;
   never trigger it from backend changes.
4. Local Supabase stack + pgTAP requires Docker Desktop — **not currently
   installed on the dev machine**; install before Phase 1 RLS testing.
