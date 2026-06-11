# Munch — Data Model

> Phase 0: planned schema. Phase 1 turns this into versioned migrations with
> RLS enabled in the same migration as every CREATE TABLE (DECISIONS.md D-012),
> verified by pgTAP. This document then tracks the live schema exactly.

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
