# Munch — MVP-1 Free Demo Guide

> **Lands at the end of Phase 4** (the ★ FREE DEMO MILESTONE). This stub
> defines what the deliverable will contain so the bar is fixed in advance.

When Phase 4 closes, this document will walk you (and Mohamed-Amin) through:

1. **On-device demo** — installing the development build on a physical iPhone
   (this is the primary demo path: the dev machine is Windows, so there is no
   local simulator — see DECISIONS.md D-001).
2. **CI demo artifacts** — the simulator screen recording + screenshot suite
   produced by the macOS CI job for every `ios/**` change.
3. **The full click-through script** — new user → onboarding (cuisines →
   anchors → mode) → swipe deck → match → Apple Maps deep link, running
   entirely on the seeded open-data DB with **zero paid API usage** (reasons
   come from the templated fallback when no Anthropic key is set).
4. **Cost proof** — the running demo uses: Supabase free tier + Cloud Run free
   tier + seeded open data. The only money in the system is the $99/yr Apple
   Developer Program (D-003).
