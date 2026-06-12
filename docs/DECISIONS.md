# Munch — Decision Log

Deviations from the master spec, each verified against primary sources at
kickoff (2026-06-11) before Phase 0. Format: decision, why, what it replaces.

---

## D-001 — Windows-authored repo, macOS verification in CI

**Decision:** All code is plain text authorable on Windows. The Xcode project
is defined in `ios/Munch/project.yml` (XcodeGen) and generated in CI;
`.xcodeproj` is git-ignored. Pure logic lives in the MunchKit SwiftPM package
(testable via `swift test` on Linux/Windows). iOS builds, simulator tests, and
TestFlight archives run on GitHub Actions `macos-26` runners.
**Why:** The development machine is Windows 11. Xcode, the iOS SDK, simulator,
and codesigning are macOS-only, and the Windows Swift toolchain has no SwiftUI.
**Replaces:** The spec's implicit assumption of a local Mac. The "runs on iOS 17
simulator" gate becomes: headless simulator tests + screenshot artifacts in CI,
plus on-device smoke tests via development/TestFlight builds on a physical iPhone.
**Cost note:** Free GitHub plan ≈ 200 real macOS minutes/month (~20–35 builds);
`ios-build.yml` is path-filtered to `ios/**` and the Linux `verify` job is the
default gate.

## D-002 — Cloud Run replaces Fly.io/Railway for the reco service

**Decision:** The FastAPI service targets Google Cloud Run's always-free tier.
**Why:** Verified June 2026: Fly.io removed free tiers for new accounts (2024);
Railway is a one-time $5/30-day trial then $5/mo. Cloud Run's free tier
(2M req/mo) has no expiry and allows commercial use. Cold starts of a few
seconds are acceptable because deck requests are pre-fetched.
**Replaces:** Spec §2 "deploy to Fly.io or Railway".

## D-003 — Honest cost floor: $99/yr Apple, everything else $0

**Decision:** Accept the Apple Developer Program fee as the project's only
unavoidable cost (~$8.25/mo amortized). Enrollment starts in Phase 0/1 — the
Sign in with Apple *entitlement* requires a paid team, so it gates Phase 3
auth work, not just Phase 6 distribution.
**Why:** TestFlight requires the paid program; free Apple IDs cannot use the
SIWA capability at all.
**Replaces:** Spec §0/§2 "v1 must cost $0 to run" — true for infrastructure
and data, false for Apple distribution. Recorded so nobody re-litigates it.

## D-004 — LLM moves off the serve path; templated reasons are the default

**Decision:** Decks always serve instantly from the ranker with deterministic
templated reasons. Haiku pre-generates richer reason text asynchronously,
cached in Postgres keyed by (restaurant, taste-archetype, mode) with a long
TTL; the Batches API handles bulk refresh at 50% cost. The LLM path sits
behind a feature flag, default off. A spend cap is configured in the Anthropic
Console before the API key is created.
**Why:** Verified: a 20-candidate rerank + 5 reasons is realistically
1.5–2.5s p50 end-to-end — the spec's 1.5s inline timeout would make the
fallback fire most of the time while still paying for dead LLM calls. Live
rerank at 1k calls/day would also be ~$40–110/mo, the largest cost in the stack.
**Replaces:** Spec §7.6 inline rerank with 1.5s timeout. The LLM no longer
reorders visible decks at all (mid-session reordering is also a UX hazard);
it only enriches reason text.

## D-005 — Geofabrik PBF extracts replace Overpass for seeding

**Decision:** The seed/re-sync pipeline downloads Geofabrik daily extracts
(New York ~468 MB, Massachusetts ~293 MB) and filters with osmium. Overpass
is used only for ad-hoc development queries.
**Why:** Overpass public instances prohibit application-backend use and were
observably flaky during verification. Extracts are reproducible and offline.
**Replaces:** Spec §2 "seed from OSM via the Overpass API" (intent preserved:
same data, sturdier transport).

## D-006 — Re-sync runs as a GitHub Actions cron, with safety rails

**Decision:** Weekly re-sync is a scheduled Linux workflow, not a Supabase
edge function or pg_cron job. Rules: pg_dump artifact before any write
(free tier has no backups); idempotent upserts keyed on (osm_type, osm_id);
tombstones (`is_active=false`) instead of deletes so swipe-history FKs
survive; fuzzy-match decisions persisted in a match table so re-runs cannot
re-link swipe history to a different restaurant; a keepalive query so the
free Supabase project never hits the 7-day inactivity pause.
**Why:** Edge functions cap at ~2s CPU / ~256 MB — the PBF extracts alone
exceed that. The pause/no-backup behaviors are verified free-tier facts.
**Replaces:** Spec §6.4 "scheduled re-sync (e.g., weekly cron)" — same intent,
concrete execution home and failure-mode rails.

## D-007 — The synthetic eval harness is plumbing validation, not lift evidence

**Decision:** The simulator gives synthetic users latent signals deliberately
NOT in the ranker's feature set (satiation, mealtime context, unobserved
"vibe", popularity herding) plus 10–20% label noise. Metrics are reported
against a random-ranker floor and an oracle ceiling. `ALGORITHM.md` labels all
synthetic results as plumbing validation. Champion promotion of the learned
ranker requires real logged swipes (target: ≥50k swipes / ≥5k mixed-label
decks); until then the heuristic is the designated champion.
**Why:** If the simulator's preference model is expressible in the feature
set, LambdaMART "beats" the heuristic by construction — it measures agreement
with the simulator, not user value.
**Replaces:** Spec §7.4/§7.5 promotion gate "must beat champion on NDCG@5" —
kept for plumbing regression, demoted as promotion evidence.

## D-008 — LambdaMART specifics pinned before any training code exists

**Decision:** One ranking group = one served deck (`reco_events` row).
Explicit `label_gain = [0, 1, 5]` for left-swipe / right-swipe / conversion.
Unseen cards in abandoned decks are EXCLUDED from training, never labeled
negative. Card position is logged per impression for bias correction.
Train/validation splits are temporal and per-user.
**Why:** These are the four silent-failure points of swipe-app LTR; defaults
get them wrong (LightGBM's default gain is 2^label−1, and labeling unseen
cards negative is the classic logging bug).

## D-009 — internal_score: Beta-smoothed, with exploration to break rich-get-richer

**Decision:** `internal_score` = Beta posterior mean with prior strength ≈20
effective impressions centered on the live global right-swipe rate
(≈Beta(6,14) at a 30% base rate); conversions count as extra pseudo-successes;
~90-day decay. Deck assembly adds: Thompson sampling on the internal-score
component, 2 of 10 slots reserved for under-shown/novel-cuisine candidates,
max 3 cards per cuisine per deck, and a logged `explore` flag per impression.
**Why:** Sparse two-city data makes raw ratios degenerate (1/1 beats 45/60),
and without exploration the 0.40 cuisine weight + swipe-fed scoring permanently
starves new restaurants. The explore flag also enables unbiased offline
evaluation on real data later.
**Replaces:** Spec §7.3 (which had smoothing but no formula, and no
exploration mechanism at all).

## D-010 — Data-hole policies for the $0 stack

**Decision:**
- **Price:** OSM price data is literally zero (verified live: 0 of 15,051 NYC
  POIs). Impute tier from category+cuisine+neighborhood with an `imputed`
  flag; missing price passes all price filters; `price_fit` is downweighted
  when imputed; one-time manual labeling pass over the curated seed set.
- **Hours:** ~half of POIs lack `opening_hours`. Three-state open/closed/
  unknown; unknown PASSES the open-now filter with a small score penalty and
  an "hours unknown" badge.
- **Delivery ETA / dine-in wait time:** no lawful free source. Show distance
  instead of fabricated minutes; wait time is dropped from v1.
- **Conversion CTAs:** Apple Maps URL is the primary deep link (reliable,
  key-free). DoorDash/Uber Eats links are search URLs labeled as search;
  conversions are logged honestly as "outbound taps".
**Why:** Each of these fields was assumed by spec §1/§7 filters but has no
free, legal data source; verified June 2026.

## D-011 — Boston metro definition

**Decision:** "Boston" = city of Boston + Cambridge, Somerville, Brookline,
Allston (OSM coverage). Health-inspection enrichment applies to Boston city
records only (Analyze Boston's scope); the Active Food Establishment Licenses
dataset is the primary Boston join, not the legacy violation-level table.
**Why:** Boston city proper has only ~1,500 OSM restaurant POIs and excludes
where students actually eat; the legacy inspections table has no cuisine
field, text coordinates, and 2006-era inactive licenses.

## D-012 — RLS enabled in the same migration as every CREATE TABLE

**Decision:** No table is ever created without RLS enabled in the same
migration file, including dormant tables (`sponsorships` is the trap).
Verified by pgTAP tests (`supabase test db`) and a clean
`rls_disabled_in_public` advisor check as a phase-gate item.
**Why:** Supabase auto-exposes public-schema tables via PostgREST to anon-key
holders, the anon key ships in the IPA, and SQL-created tables default to RLS
OFF. A dormant unprotected table is publicly read/writable with nothing
exercising it to surface the hole.

## D-013 — Account deletion includes Apple token revocation (TN3194)

**Decision:** The Apple refresh token is captured and stored (encrypted) at
first sign-in; `delete-account` purges user rows AND calls Apple's
`/auth/revoke`. Schema support lands in Phase 1 — tokens never stored cannot
be revoked later.
**Why:** Apple requires token revocation on account deletion for SIWA apps;
deleting the Supabase auth row alone is non-compliant.

## D-014 — Age rating: 13+ (not the spec's "17+")

**Decision:** Target the 13+ tier under Apple's current (post-July-2025)
13+/16+/18+ system, finalized via the mandatory rating questionnaire in
Phase 6 (alcohol-venue exposure is the deciding question).
**Why:** Apple retired the 12+/17+ tiers; the spec's instruction predates that.

## D-015 — `eval/` renamed to `evalharness/`

**Decision:** The Python eval package is `backend/reco/evalharness/`
(`python -m evalharness.run`), not the spec's `eval/`.
**Why:** `eval` shadows a Python builtin as a top-level module name — it
confuses tooling, IDE resolution, and readers. Pure naming-hygiene deviation;
the spec's contract (reproducible CLI run + metrics table) is unchanged.

## D-017 — Grant posture pinned explicitly in migrations

**Decision:** Migration `20260611120006_grants` explicitly grants
table/sequence/routine access to `anon`/`authenticated`/`service_role` and
pins matching default privileges, instead of relying on Supabase's implicit
default-privilege setup.
**Why:** The pgTAP suite caught the local CLI stack applying migrations under
a role whose objects got no automatic grants — local and hosted diverged.
Grants are the *exposure* layer; RLS remains the *security* boundary, and the
broad grants are safe precisely because of D-012 (RLS on every table at
creation; deny-all on service-only tables).
**Replaces:** Implicit reliance on platform default privileges.

## D-018 — Boston inspection ref is a composite (no license number exists)

**Decision:** `source_matches.inspection_ref` for Boston rows is
`property_id:licensecat:nameslug`.
**Why:** Verified live (2026-06-11): the Active Food Establishment Licenses
dataset has no license-number column, and CKAN's `_id` renumbers on
re-upload. Multiple licenses share one property (food halls, per-floor
cafes), so property id alone is not unique. The composite is stable across
re-uploads as long as the venue keeps its name and category — acceptable for
an enrichment join, revisit if Boston restores a license-number field.

## D-020 — Eval NDCG grades against clean truth, not the noisy draw

**Decision:** The synthetic eval grades NDCG against each venue's **noise-free
expected utility**; observation noise lives only in the binary labels
(right/left flips). The oracle ranks by that same clean signal and is therefore
NDCG 1.0 by definition — an idealized perfect-knowledge reference.
**Why (a Phase-2 adversarial review caught this):** the first version stored a
single *noisy* utility draw, had the oracle sort by it, and graded NDCG against
that same column — so the oracle was trivially perfect and the heuristic→oracle
gap was falsely attributed to the hidden `vibe` term (zeroing `vibe` closed only
~0.013 of the 0.167 gap). The real gap is the heuristic's thin taste projection
(anchors + adjacency, not the full per-cuisine utility vector) plus label noise.
**Consequence:** the bracket is now honest — random floor < heuristic <
idealized ceiling — and the docs/docstrings attribute the gap correctly. The
oracle's 1.0 is explicitly a definitional ceiling, not an achievable target.
Refines D-007; does not change the spec's metric list.

## D-019 — Backend pivots from Supabase/Postgres to Firebase

**Decision:** The live backend is Firebase (Firestore + Firebase Auth +
Cloud Run for the reco service), not Supabase/Postgres. Confirmed by Mirza
2026-06-11 after the borrowed free Supabase org hit its 2-project cap.
**Carries over unchanged:** every DB-agnostic piece — the entire seed
*processing* pipeline (OSM extraction, inspection fetch, fuzzy matching,
cuisine canonicalization, curation, dedup) and ALL of Phase 2 (filters,
heuristic scorer, eval harness). None of it ever touched the database.
**Rewritten (persistence + security only):** Postgres migrations → Firestore
collections + composite indexes; RLS policies → Firestore Security Rules;
pgTAP → @firebase/rules-unit-testing; seed `emit.py` SQL writer → a Firestore
document writer that stamps a geohash per venue. DATA_MODEL.md's schema
*design* is retained; the SQL is not.
**Geospatial cost (real):** Firestore has no PostGIS. "Restaurants near me"
uses geohash-range queries (geofire-common pattern) with precise distance +
cuisine/price/open-now filtering applied in the reco service after fetch.
Viable at ~800 venues/metro; weaker than PostGIS, accepted.
**Architecture simplification:** client→Firestore writes guarded by Security
Rules (swipes/conversions) + the FastAPI reco service reading Firestore via
the Admin SDK collapse the separate edge-function tier. get-deck logic lives
in the reco service (Cloud Run free tier), not edge functions.
**Cost catch:** Firestore + Auth are free (Spark); Cloud Functions need the
Blaze plan (card on file, free allowance). Staying on Cloud Run keeps the
billing surface minimal.
**Supersedes the Supabase specifics of:** D-002 (hosting), D-006 (re-sync
home is still a GitHub Actions cron, now writing Firestore), D-012/D-017
(RLS/grants → Security Rules), D-013 (account deletion still needs Apple
TN3194 token revocation, now via the Firebase Admin SDK + a server call).
The Postgres migrations + pgTAP suite remain in git history for reference.

## D-016 — `web/` directory added to the spec §3 layout

**Decision:** A top-level `web/` directory (GitHub Pages) is added to the
repo layout.
**Why:** TestFlight external testing cannot start without a hosted Privacy
Policy URL and support contact in App Store Connect (Beta App Information),
and the spec's layout had no web property anywhere. GitHub Pages is the $0
hosting answer; it also gives the ODbL attribution obligation a public home.
**Replaces:** Nothing in the spec — pure addition, recorded so the layout
audit trail stays complete.
