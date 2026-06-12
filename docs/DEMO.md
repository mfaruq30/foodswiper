# Munch — Free MVP-1 Demo (★ the Phase 4 milestone)

How to run and click through the complete product loop — onboarding → swipe →
match → deep link — at **$0**, on the seeded open-data restaurants, with **no
Firebase, no Apple Developer account, and no API keys**. This is the demo for
Mirza and Mohamed-Amin.

## What you're demoing

1,600 real NYC + Boston restaurants (OpenStreetMap + city open data), ranked
per-user by the Munch heuristic (cold-start anchors → cuisine affinity →
distance/price/quality), served as a swipe deck with a one-line reason per
card, exploration slots, and a match moment with real conversion CTAs.

## Piece 1 — the backend (runs on ANY machine, incl. this Windows PC)

```sh
cd backend/reco
# Full inventory (after a seed run produced seed_out/venues.ndjson):
MUNCH_BACKEND=memory MUNCH_AUTH=dev \
  VENUES_NDJSON=../supabase/seed/seed_out/venues.ndjson \
  uv run -- uvicorn app.main:app --port 8123

# No seed run handy? Use the committed 100-venue sample instead:
#   VENUES_NDJSON=fixtures/venues.sample.ndjson
```

PowerShell equivalent:

```powershell
cd backend\reco
$env:MUNCH_BACKEND="memory"; $env:MUNCH_AUTH="dev"
$env:VENUES_NDJSON="..\supabase\seed\seed_out\venues.ndjson"
uv run -- uvicorn app.main:app --port 8123
```

Sanity check: `curl localhost:8123/health` → `{"status":"ok",...}`.
Memory backend + dev auth = zero external services, zero cost (D-019/D-003).

## Piece 2 — the app

**Option A — a Mac is available (best demo):**

```sh
brew install xcodegen
cd ios/Munch && xcodegen generate && open Munch.xcodeproj
```

Run the `Munch` scheme on an iOS 17+ simulator. The app defaults to
`http://localhost:8123` — with the backend from Piece 1 running on the same
Mac, it just works. (Backend on another machine? Set the `MUNCH_API_URL`
scheme environment variable to `http://<that-machine-ip>:8123`.)

**Option B — no Mac (this dev machine):** the same flow runs headlessly on
GitHub Actions — trigger the **ios-e2e** workflow (Actions tab → ios-e2e →
Run workflow). It boots the API + simulator and drives onboarding → deck →
3 right-swipes → match; the green run is the demo certificate, and failure
artifacts include the API log.

**Option C — your iPhone:** needs the Apple Developer account (in progress);
then a development build installs directly and TestFlight follows in Phase 6.

## The click-through script (~90 seconds)

1. **Welcome** — "Stop deciding. Start eating." → *Get started*.
2. **Cravings** — pick 5+ cuisines (try Pizza, Italian, Ramen, Korean, Burgers).
3. **Favorites** — type `luc` → tap **Lucali** (a real Carroll Gardens pizza
   spot; this is the cold-start anchor). Optional but it visibly sharpens the deck.
4. **Mode** — Dine in → *Start swiping*.
5. **The deck** — real Greenwich Village restaurants, each with a reason line
   ("You love Pizza — this one's 0.3 mi away"). Two cards per deck are marked
   **DISCOVER** — the exploration slots that keep tastes from narrowing.
   Location permission declined? It says so and uses the metro center.
6. **Swipe** — drag, or use the ✕ / ♥ buttons. On the **third** right-swipe:
7. **It's a match** — the best of your yes-es, with *Directions* (Apple Maps),
   *Call* where the venue has a number, or delivery/pickup search links.
   Every tap is honestly logged as an outbound tap (D-010).
8. **Profile tab** — your taste, dietary filters (these hard-filter decks),
   Privacy/Terms, **Data sources** (the ODbL attribution), and
   **Delete my account** — which really purges everything (D-013).

Boston works identically: pick Boston in onboarding (try anchors `isshindo`
or `santouka` near BU).

## What this demo is NOT (honest scope)

- Reasons are the deterministic templates — the LLM-written ones are Phase 5.
- Rankings are the cold-start heuristic; the learned ranker needs real swipes.
- All prices are imputed (open data has none) — shown with a `?` (D-010).
- Hours are unparsed in v1, so no "closed now" filtering yet (Phase 5).
