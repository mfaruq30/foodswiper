# Munch

Swipe-based personalized restaurant discovery for NYC + Boston. Learns each
user's taste across three modes — dine-in, pickup, delivery — and surfaces the
single best next match with a specific, human-readable reason.

**Status: Phase 0 (scaffold).** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
for how the pieces fit and [docs/DECISIONS.md](docs/DECISIONS.md) for every
deviation from the original spec and why.

## Repository map

| Path | What it is | Toolchain |
|---|---|---|
| `ios/Munch/` | SwiftUI app (iOS 17+, MVVM). Project generated from `project.yml` by XcodeGen — `.xcodeproj` is never committed | Swift 5.10, SwiftLint, SwiftFormat |
| `ios/Munch/Packages/MunchKit/` | Pure-logic SwiftPM package (domain models, scoring/gesture math) — testable without the iOS SDK | `swift test` |
| `backend/supabase/` | Postgres + PostGIS migrations, RLS policies, Deno edge functions, open-data seed pipeline | Deno 2, Supabase CLI, pgTAP |
| `backend/reco/` | FastAPI recommendation service: filters → heuristic scorer → learned ranker, plus the offline eval harness (`evalharness/`) | Python 3.12, uv, ruff, mypy --strict, pytest |
| `legal/` | Privacy policy / ToS / EULA drafts (attorney review required before launch) | — |
| `web/` | GitHub Pages site: hosted privacy policy, support page, OSM/ODbL attribution | — |
| `docs/` | Architecture, algorithm iteration log, data model, runbook, demo guide | — |

## Quick start (any platform)

```sh
# Everything: lint + type check + test, all stacks. The phase gate.
make verify            # or directly: bash scripts/verify.sh

# Tests only (fast inner loop)
make test              # or: bash scripts/verify.sh --tests-only
```

Requirements: [uv](https://docs.astral.sh/uv/) (manages Python 3.12 + deps
automatically) and [Deno 2](https://deno.com/). Swift/SwiftLint/SwiftFormat are
optional locally — `verify.sh` reports them as loud SKIPs where absent; CI
(`VERIFY_STRICT=1`) enforces them.

### The Windows ↔ macOS split (read this once)

This repo is **authored on Windows, verified on macOS CI**. Xcode does not run
on Windows, so:

- The Xcode project is *defined* in [ios/Munch/project.yml](ios/Munch/project.yml)
  and *generated* in CI by XcodeGen. Never commit a `.xcodeproj`.
- Pure logic goes in **MunchKit** (testable everywhere). SwiftUI/UIKit code
  compiles only in the macOS CI job ([.github/workflows/ios-build.yml](.github/workflows/ios-build.yml)),
  which is path-filtered to `ios/**` because macOS minutes cost ~10× Linux.
- Line endings are LF everywhere, enforced by `.gitattributes`. Don't fight it.

### Per-component dev loops

```sh
# Recommendation service (backend/reco) — uv syncs the venv on first run
cd backend/reco
uv run --extra dev -- pytest                  # tests
uv run --extra dev -- uvicorn app.main:app    # serve on :8000

# Edge functions (backend/supabase/functions)
cd backend/supabase/functions
deno test && deno lint && deno fmt --check

# MunchKit (requires a Swift toolchain)
swift test --package-path ios/Munch/Packages/MunchKit
```

## Secrets

None required to run the demo path. `.env.example` documents every variable;
the app degrades gracefully without the optional Anthropic key (templated
reasons). See spec rule: no secret ever enters this repo.

## Phase gates

Work proceeds in spec-defined phases (0–8), each ending with `make verify`
green and an explicit go/no-go. Current gate evidence lives in the phase
summary posted at the end of each phase.
