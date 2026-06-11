# Claude Design Prompt — Final Deliverable (Phase 8)

> Written **last**, per spec §14, after every screen, component, and state
> exists in the real app — so the design prompt describes what was actually
> built, not what was planned. Producing it earlier would freeze guesses.

Contract for the finished artifact (fixed now so Phase 8 can't lower the bar):

- Self-contained: paste-able into a fresh Claude Design session with no memory
  of this build — embeds actual token values and the full screen inventory.
- Covers: role + context; every screen with all states (empty/loading/error/
  success); the design-token sheet (colors hex, type scale with the chosen OFL
  fonts, spacing, radii, elevation, motion); the reusable component kit
  (SwipeCardStack, CuisineGrid tile, AnchorRestaurant row, ModeTabs, MatchCard,
  AltItem row, ReasonChip, buttons, progress, empty/loading/error states).
- Hard constraints: SwiftUI-implementable, iOS 17 HIG, Dynamic Type + 44pt
  targets + contrast, light mode first, honest "Featured" treatment for
  sponsored cards.
- **Placeholder card art is a first-class design-system deliverable** — with
  ~0.04% real photo coverage in the seed data, the cuisine-keyed
  gradient/illustration system IS the product's visual identity (D-010 /
  kickoff photo finding), not a fallback.
