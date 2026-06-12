# Munch — Data Model

> **Live backend: Firebase/Firestore (D-019), project `food-5eb2a`.** The
> Postgres schema below it remains the design reference and the
> migration-back path — the SQL migrations + pgTAP suite stay in git.

## Firestore collections (Phase 3, live)

| Collection | Doc id | Contents | Written by |
|---|---|---|---|
| `venues/{id}` | `osm:<type>:<id>` (stable across re-seeds & backends) | canonical venue fields + derived `geohash`, `name_lower`, `is_active` | seed writer only |
| `venue_scores/{id}` | same as venue | `impressions`, `rights`, `internal_score` (decayed posterior) — Munch-owned; created once, never reset by re-seeds | API / weekly job |
| `profiles/{uid}` | Firebase auth uid | taste profile incl. server-maintained `recent_right_cuisines` | API |
| `swipes`, `conversions`, `feedback`, `reco_events` | auto | append-only events (card_position + explore on swipes, D-008) | API |

**Security model:** `firestore.rules` is **deny-all for clients** — the iOS
app speaks only the Munch HTTP API (Cloud Run, Admin SDK). No per-collection
rules to audit because there is no client surface; this is also the
portability seam (D-019).

**Canonical artifact:** `venues.ndjson` (seed pipeline output) is the
backend-neutral source of truth — plain WGS84 lat/lon floats, no geohash, no
backend fields. Both the Firestore writer and any future Postgres writer
consume it. Composite indexes: `firestore.indexes.json`.

---

## Postgres reference schema (superseded by D-019, retained for migration-back)

> Phase 1 implemented this fully: versioned migrations with RLS enabled in the
> same migration as every CREATE TABLE (D-012), verified by pgTAP in CI.

## Conventions

- Every table: RLS enabled at creation. Users read/write only their own rows;
  restaurant data is world-readable, write-restricted to the service role.
- ODbL hygiene (D-005 + kickoff licensing finding): the merged venues table
  (OSM ⋈ inspections) is treated as redistributable ODbL data. **Proprietary
  signals (`internal_score`, curation flags) live in separate tables keyed by
  restaurant id — never as columns on the merged table.**
- Geography: PostGIS `geography(Point, 4326)`, GiST-indexed.

## Planned tables (amendments over spec §5 noted inline)

| Table | Purpose | Notable columns / amendments |
|---|---|---|
| `profiles` | One row per auth user | `home_metro enum('nyc','boston')`, dietary_flags jsonb. **Adds `apple_refresh_token` (encrypted) — required for TN3194 revocation on delete (D-013)** |
| `user_preferences` | Per-mode taste weights | cuisine_weights jsonb, price_pref, updated_at |
| `restaurants` | Seeded venues (OSM + open data) | osm_type+osm_id unique, cuisines text[] (canonicalized), `price_tier` + **`price_imputed` bool (D-010)**, hours jsonb + **`hours_known` bool**, location geography, metro, source enum, popularity_prior, **`is_active` tombstone (D-006)**. No third-party ratings, ever |
| `restaurant_scores` | **Separate from `restaurants` for ODbL hygiene** | internal_score (Beta posterior), impressions, rights, conversions, updated_at |
| `source_matches` | **New (D-006): persisted fuzzy-match decisions** | osm ref ↔ inspection ref (CAMIS / license #), match_confidence, decided_by enum('auto','manual') |
| `anchor_restaurants` | Cold-start anchors | source enum('onboarding','conversion') |
| `swipes` | Every swipe | direction, mode, session_id, context jsonb, **`card_position` int + `explore` bool (D-008/D-009)** |
| `conversions` | Outbound taps | conversion_type — logged honestly as outbound taps, not confirmed orders (D-010) |
| `feedback` | Post-visit rating | -1/0/1 |
| `sponsorships` | Paid placement rules (no admin UI in v1) | RLS from creation — this dormant table is the canonical leak trap (D-012) |
| `reco_events` | **The training/eval log** — every served deck | request_id, candidate_ids, served_order, model_version, latency_ms |
| `reason_cache` | **New (D-004): pre-generated LLM reasons** | (restaurant_id, archetype, mode) key, reason text, expires_at |

## Indexes (Phase 1)

GiST on `restaurants.location`; btree on all FKs, `swipes.created_at`,
`reco_events.created_at`; partial index on `restaurants(metro) WHERE is_active`.

## RLS policy sketch

| Table | anon | authenticated | service_role |
|---|---|---|---|
| restaurants, restaurant_scores | read | read | all |
| profiles, user_preferences, swipes, conversions, feedback, anchor_restaurants | none | own rows (`auth.uid()`) | all |
| sponsorships, reco_events, source_matches, reason_cache | none | none | all |
