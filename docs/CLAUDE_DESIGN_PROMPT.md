# Munch — Claude Design Prompt (Phase 8, modern/Gen-Z direction)

> Self-contained brief for a fresh Claude Design session. It embeds the app's
> actual shipped tokens/screens/components (verified from `Theme.swift`,
> `Components.swift`, `CardArt.swift`, and the 8 feature screens) **and** every
> design decision pre-answered, so no intake questions are needed. Paste the whole
> thing. A first pass came back beautiful but too conservative (print-magazine
> restraint); this version steers it to a modern, kinetic, crave-worthy app.

---

## 1. ROLE & MISSION

You are a senior product designer + motion designer creating the visual system for
**Munch** — a swipe-based restaurant-discovery iPhone app for **New York City and
Boston**, aimed at **18–30-year-olds** (launching around college campuses, BU first).
Users set what they're craving, then swipe through *real* nearby restaurants
Tinder-style until they match on one to eat at.

The app is already built and functional in **SwiftUI (iOS 17+, targeting iOS 26),
iPhone-only**. A real design system exists — your job is to **elevate it into
something modern and exciting**, not invent from scratch.

**The goal: modern, tactile, kinetic, crave-worthy.** It should feel like an app a
20-year-old opens ten times a day — confident color, real depth, satisfying motion,
and food art that makes you hungry. **Anti-goals:** (1) a quiet print-magazine /
boutique brand book (the last pass's mistake — cream whitespace, tiny framed
elements, monogram card art, one muted orange); (2) a generic, cold delivery app
(Uber Eats / DoorDash are the *foil*, not the model). Munch is warm and human, but
*alive*.

## 2. DECISIONS — already made (do not ask, just execute)

- **Focus, in order:** (1) the **cuisine card-art system** (the product's whole visual
  identity), (2) the **swipe deck + match moment** (the signature screens), then (3)
  the full component kit + remaining screens.
- **Presentation:** deliver **BOTH** — polished **device-framed screens** (so it reads
  as a real app) **AND** a flat **design-system spec board** (tokens + components +
  card-art system) for the engineer.
- **Card-art directions:** produce **2** — (a) *vibrant evolution* and (b) *bold take*
  (defined in §5). Both keep the deterministic per-cuisine rule.
- **How far past flat gradient + emoji:** **all the way.** Kill raw emoji AND the
  monogram. Use **mesh/layered gradients + a custom illustrated food glyph per cuisine
  + subtle grain**. This is the single highest-impact change.
- **Screens rendered in full:** **all key screens, every state**, prioritizing the
  **swipe deck** and **match**.
- **Motion:** **show it** — a **working/interactive swipe demo** and an **animated
  match-moment reveal**; specify motion + haptics for every signature interaction.
- **Token freedom:** **refine values where it clearly helps and expand the system**
  (richer gradients, per-cuisine hues, a paired modern sans, an optional dark surface)
  — but **keep the token names and the warm-orange brand DNA**, and justify changes.
- **App icon:** deliver **2–3 bold, modern concepts** in the new card-art language
  (drop the monogram seal).
- **Founder context:** the founder develops on **Windows and cannot run the app**, so
  the device-framed screens + the interactive swipe demo are how this gets judged —
  make them feel real.

## 3. AESTHETIC NORTH STAR + REFERENCES

Warm, appetite-forward, confident, kinetic, premium-but-playful. Match the *feeling*
of these, don't copy them:
- **Cash App / Spotify (Wrapped) / Partiful** — fearless saturated color, huge
  confident type, personality over restraint.
- **iOS 26 Liquid Glass** — translucent, frosted, depth-layered chrome (floating glass
  tab bars, glass buttons, sheets that morph). This is the modern *native* look — lean in.
- **Gopuff / Gorillas / modern food branding** — vivid, crave-worthy, fun.
- **Duolingo / BeReal** — springy, characterful micro-interactions and reward moments.
- **Airbnb / Headspace** — depth and warmth done premium, never flat.

## 4. BRAND FOUNDATIONS (shipped tokens — keep the names; expand, don't discard)

Light-mode-first today; **add a dark "night" mode** in this pass (food pops on dark and
the audience leans dark). Display type is **Fraunces** (SIL OFL, bundled); body is the
native SF Pro stack for Dynamic Type — **pair Fraunces with a clean modern
geometric/grotesque sans** for UI labels so it reads contemporary, not bookish.

**Color (current, keep as the base):**
| Token | Hex | Role |
|---|---|---|
| `Theme.paper` | `#FAF6F0` | App bg — warm off-white (light mode) |
| `Theme.surface` | `#FFFDF9` | Card/row surface (light) |
| `Theme.ink` | `#2B2118` | Primary text — warm near-black |
| `Theme.inkSecondary` | `#6E5F51` | Secondary text |
| `Theme.accent` | `#E8552E` | Brand warm-orange — CTAs, selection, brand moments |
| `Theme.accentSoft` | `#FBE3DB` | Soft accent tint |
| `Theme.yes` | `#2E8B57` | Right-swipe affirmation (green) |
| `Theme.nope` | `#C0392B` | Left-swipe / destructive (red) |
| `Theme.stroke` | `#E8DFD3` | Hairlines, borders, disabled fills |

**Expand the palette (this pass):** keep `#E8552E` as hero, but design a **richer
multi-stop gradient ramp** off it and **per-cuisine accent hues** (so the deck is varied,
not one orange). Propose a **dark "night" set** — e.g. a deep warm near-black bg
(~`#161210`), surface ~`#221C17`, text cream `#FAF6F0`, accent unchanged (pops on dark);
finalize values for AA contrast and show both modes.

**Type scale (current):** `munchTitle` Fraunces 34 · `munchHeading` Fraunces 24 ·
`munchCardName` Fraunces 28 · `Theme.display(size)` parametric. **Push display sizes
bigger and bolder** for hero moments (sign-in, match). Body/meta = SF Pro (or your paired
sans) at `.headline`/`.subheadline`/`.body`/`.footnote`/`.caption`.

**Spacing (4pt base):** 4 · 8 · 12 · 16 · 24 · 32 · 48. **Radii:** `radiusCard` 24 ·
`radiusControl` 14 · `radiusChip` 999 (capsule). **Elevation:** today one shadow
(`ink` @10%, radius 18, y 8) — **add real depth** (layered/soft shadows, glass blur).

## 5. CARD-ART SYSTEM — the heart of the brief

Restaurant photos are ~**0% in the data**, so cards never show photos — **the card art
IS the product's visual identity.** The current implementation (your starting point, to
be replaced): a `LinearGradient` (`.topLeading→.bottomTrailing`) with a big centered
**emoji** OR a letter monogram-in-a-circle, filling the top ~46% of the card. **Both the
raw emoji and the monogram must go** — they read unfinished and corporate.

**Build a system that is deterministic, cuisine-coherent, and crave-worthy:**
- **Deterministic:** a venue's `id` hash picks one of N variants for its cuisine family,
  so the same venue always looks identical and adjacent same-cuisine cards don't clone.
- **Composition:** **near-full-bleed** art (immersive, not a small framed rectangle), a
  **rich mesh/layered gradient** background, a **large expressive custom food glyph**
  centered/offset, **subtle grain + a soft light bloom** for tactility, and a **gradient
  scrim** at the bottom so name/price/reason stay legible over the art.
- **Custom glyphs, per cuisine** (illustrated marks — clean line + fill with slight
  dimensionality, an ownable set; NOT emoji, NOT letters): pizza = a slice; italian =
  a pasta swirl; ramen = a steaming bowl + chopsticks; sushi = nigiri; japanese = bento;
  chinese = takeout box / dumpling; korean = stone bowl; thai = curry bowl; mexican =
  taco; burger = burger; american = stacked sandwich; indian = curry + naan;
  mediterranean = olive branch / pita; middle_eastern = skewer; seafood = lobster/fish;
  dessert = layered cake. (~35 more cuisines exist in the catalog; design a default
  "fork/spark" glyph for unmapped ones.)
- **Gradient families (current pairs — make them mesh/multi-stop and richer):**
  - *Pizza / Italian / Mediterranean:* warm orange → red (`#F2A65A→#E8552E`, `#F7C59F→#D7263D`)
  - *Asian (japanese, sushi, ramen, korean, chinese, pan-asian, noodles, vietnamese, thai, filipino):* burnt orange → maroon (`#F67B45→#9B2226`, `#FFB385→#BC4749`)
  - *Latin (mexican, latin, caribbean, peruvian, spanish):* gold → bright red (`#F9C74F→#F3722C`, `#F8961E→#D62828`)
  - *Plant-based (vegan, vegetarian, salad, juice):* sage → teal (`#B5C99A→#55828B`, `#CFE1B9→#718355`)
  - *Sweet / brunch (coffee, bakery, dessert, breakfast, bagel, bubble tea):* cream → tan/brown (`#E6CCB2→#9C6644`, `#F1DCA7→#B08968`)
  - *Seafood:* sky → ocean (`#90C2E7→#3E7CB1`, `#A9D6E5→#2A6F97`)
  - *Default (unmapped):* warm orange → brown (`#F2A65A→#BC6C25`, `#F7B267→#99582A`)

**The two directions to deliver:**
- **(a) Vibrant evolution** — refined mesh gradients + the custom glyph set + grain.
  Safe, premium, ships easily. Light + dark.
- **(b) Bold take** — full-bleed illustrated/3D-leaning food art, **dark-surface
  default**, maximal energy and depth (the "wow" version). Show this is still legible
  and performant.

## 6. COMPONENT KIT (refresh each with depth, glass, and full states)

All controls: ≥44pt targets, VoiceOver labels + stable `accessibilityIdentifier`,
Dynamic Type. Show every state.
- **PrimaryButton** — brand CTA. `accent` fill, white `.headline`, `maxWidth:.infinity`,
  `minHeight:54`, `radiusControl`. Disabled = `stroke` fill / `inkSecondary` text. Add a
  satisfying pressed state (scale + haptic).
- **SecondaryButton** — outline, `ink` text, `stroke` 1.5pt border, no fill. Consider a
  **glass** variant for use over card art.
- **SelectableChip** — cuisine/dietary toggle. Selected = `accentSoft` fill / `accent`
  text / `accent` border; default = `surface` / `ink` / `stroke`. Capsule, 44pt.
- **GlassSegmentedControl (ModeTabs)** — Dine In / Pickup / Delivery as a **floating
  Liquid-Glass** segmented control; selected segment = `accent`.
- **ProgressDots** — onboarding step indicator; active dot 22×8 `accent`, inactive 8×8
  `stroke`. Make the transition springy.
- **ReasonChip** — *signature moment*: the "why this matches you" line. `sparkles` glyph +
  text, `accentSoft` fill, `accent` text. Make it feel special, not a generic tag.
- **PriceLabel** — `$`×tier (clamp 1–4) + `?` when imputed (estimated) — keep the honest
  `?` legible.
- **StateMessage** — full-screen empty/error/loading: icon + `munchHeading` title + body
  + optional retry. Make the empty/error states **playful and on-brand**, not sterile.
- **GlassActionButton (Pass / Like)** — circular **frosted-glass** buttons over the deck;
  Pass = `nope` `xmark`, Like = `yes` `heart`; pulse + haptic on press.

## 7. SCREENS — every screen, every state (modern treatment)

Flow: **Sign In → Onboarding (Welcome → Cuisines → Anchors → Mode) → main tabs (Swipe
deck, Profile)**, Match sheet over the deck, Legal/Data-sources off Profile. Render all
device-framed in both light and (where it sings) dark.

**Sign In** — centered: big bold "Munch" wordmark, tagline **"Stop deciding. Start
eating."**, **Sign in with Apple** (Apple's button, 54pt), legal line "By continuing you
agree to our Terms and Privacy Policy." Make the background *alive* (subtle animated
gradient / drifting card-art bloom), not flat cream. States: idle · loading (button →
spinner) · error (red message; a user-cancelled sign-in shows no error).

**Onboarding — chrome:** top bar with back + ProgressDots on steps 2–4; springy
right-to-left transitions.
- **Welcome** — playful food-glyph motif, "Munch", tagline, **"Get started"**, helper
  "About 90 seconds to set up." Give it energy and motion.
- **Cuisines (gate: pick ≥5)** — heading **"What do you crave?"**, "Pick at least 5.", a
  2-column grid of cuisine chips (each showing its custom glyph + label), a live counter
  **"{N} of 5 picked"** that turns `accent` + a satisfying tick when satisfied, Continue
  disabled until 5. Make selecting feel tactile (spring + haptic).
- **Anchors (optional, high-signal)** — **"Name a few favorites"**, "Restaurants you
  already love teach Munch your taste. This is the secret sauce." Metro segmented picker,
  glass search field, results (≤8 rows: name, cuisines joined by " · ", add/added icon;
  picked rows accent-tinted). States: idle (<2 chars) · loading · results · "No matches —
  try another spelling." Picked anchors (≤5) as a horizontal chip strip. Footer "Optional
  — but even one helps a lot." + Continue.
- **Mode** — **"How are you eating?"**, three big cards: Dine In "Table for now",
  Pickup "Grab and go", Delivery "To your door" (each with a custom glyph; selected =
  accent). Submit **"Start swiping"**. States: ready · submitting (spinner) · error
  ("Couldn't save — is the demo server running?").

**Swipe deck (the core screen) — make the card the immersive hero:**
- Chrome: "Munch" wordmark + the **glass ModeTabs**; optional honest fallback-location
  banner ("Using {metro} center — enable location for nearby picks").
- **Card stack:** top ~3 cards, staggered with real depth; the **front card is large and
  near-full-bleed.** Card = `surface` + `radiusCard` + layered shadow.
- **Card anatomy:** top ~46–60% is the **cuisine card art** (§5, immersive); over a scrim:
  restaurant **name** (`munchCardName`), a meta row (cuisine · `PriceLabel` · distance with
  a pin glyph), and the **ReasonChip**. A **"DISCOVER"** badge marks an exploration card
  (deliberately outside the user's usual taste). **Sponsored cards show a visible
  "Featured" badge — honest, never disguised.**
- **Gestures + feedback:** drag rotates the card with a **parallax tilt**; bold **YES**
  (`yes` green) / **NOPE** (`nope` red) stamps scale + rotate in with drag distance; past
  threshold the card **springs off with overshoot + a haptic tick**. Two **glass circular
  56pt** buttons (Pass `xmark`, Like `heart`) mirror the gesture.
- **States:** loading (branded spinner, "Finding spots near you…", controls hidden) ·
  error (`wifi.exclamationmark`, "Connection trouble", retry) · empty—dietary
  (`fork.knife`, "Nothing matches your filters here", "Try widening your search or relaxing
  dietary filters.", no retry) · empty—exhausted (`sparkles`, "That's everyone nearby",
  "Check back soon — or switch modes.", no retry) · active.

**Match sheet ("It's a match") — make it a dopamine moment:** the matched card **springs
up + scales**, a **spark/confetti burst** in the brand palette, a **success haptic**, and a
big kinetic **"It's a match"** (oversized Fraunces) with a soft gradient bloom behind it.
The matched venue as a large card + the reason line (accent). **Mode-specific CTAs** (each
logs a conversion before opening): Dine-In → **Directions** + **Call** (if phone known);
Pickup → **Find on DoorDash**; Delivery → **Find on DoorDash** + **Find on Uber Eats**.
Then **"Also great"** (≤2 alternate rows: glyph, name, cuisine · distance) and a **"Keep
swiping"** button. This is the screenshot people share — make it shareable.

**Profile** — sections: **Your taste** (read-only accent chips of anchor cuisines; empty →
"Pick favorites during onboarding") · **Dietary** (4 chips: Vegetarian, Vegan, Gluten-free,
Halal — optimistic toggle, revert+alert on failure; footer notes coverage is sparse) ·
**About** (Privacy Policy, Terms of Service, Data sources & attribution) · **Account**
(Home metro value or "Not set"; **"Delete my account"** destructive → confirm dialog "This
permanently deletes your profile and swipe history." / "Delete everything" / "Cancel" →
"Deleting your account…" → back to onboarding) · footnote ODbL credit "Munch demo · data ©
OpenStreetMap contributors". States: loading · error (retry) · loaded. Keep it clean but
give it the same modern surface treatment, not a plain settings list.

**Legal / Data-sources** — `ScrollView`, big heading, an `accentSoft` callout. LegalView
opens with "Plain-English summary — the full legal text ships with public launch."
DataSourcesView carries the **required attributions** (© OpenStreetMap contributors + a
working `openstreetmap.org/copyright` link [ODbL], NYC Open Data DOHMH, Analyze Boston
PDDL) and an honesty note: **"Munch's match percentages come from Munch users, never
scraped ratings."**

## 8. MOTION & HAPTICS (half the "modern" feel — specify it)

- **Swipe:** drag → live rotation + parallax tilt + stamp fade-in; release past threshold →
  spring fly-off with slight overshoot; under threshold → spring back. Haptic on commit.
- **Match:** card spring-scale-in + spark/confetti + success haptic + title kinetic reveal.
- **Micro-interactions:** every tappable has a pressed state (scale ~0.97 + soft haptic);
  chip/segment selection springs; counters tick.
- **Transitions:** springy, physical (not linear fades); onboarding steps slide+settle.
- **Reduce Motion:** provide a calm fallback (cross-fades, no parallax/confetti) — required.

## 9. HARD CONSTRAINTS

- **SwiftUI / iOS 26-buildable.** Everything must map to native APIs: `MeshGradient`,
  Liquid Glass (`.glassEffect` / glass backgrounds), `.sensoryFeedback`,
  `matchedGeometryEffect`, `PhaseAnimator`/`KeyframeAnimator`, `Canvas`, `TimelineView`,
  `.symbolEffect`. No effect that can't ship in SwiftUI.
- **Light AND dark** — design both; dark is first-class this pass.
- **Accessibility is a gate:** Dynamic Type scales (no fixed type that breaks large sizes),
  ≥44pt targets, **AA contrast** (verify text over the new vivid gradients/scrims), and the
  Reduce-Motion fallback above.
- **Honesty (non-negotiable):** sponsored = visibly "Featured"; never imply Yelp/Google
  star-rating data — Munch's match % comes only from real user swipes.
- **Performance:** the deck swipes fast — card art + motion must stay buttery (no heavy
  blur stacks that drop frames).
- **Keep the warm-orange DNA** (`#E8552E`) and the token *names*; expansions are additive.

## 10. DELIVERABLES

1. **Refined + expanded token sheet** — palette (light + dark), the gradient ramp +
   per-cuisine hues, type scale (Fraunces + the paired sans), spacing, radii, elevation,
   and **explicit motion specs**. Keep names; justify changes.
2. **Card-art system, 2 directions** (vibrant evolution + bold), with the per-cuisine
   gradient families + custom glyph set, the determinism rule, and legibility scrim.
3. **Full component kit**, all states, in the refined system (incl. the glass components).
4. **Every screen, device-framed, all states**, light + dark — leading with the **swipe
   deck** and the **animated match moment** (show the motion / make it interactive).
5. **App icon — 2–3 bold concepts** in the new card-art language (no monogram).
6. **Accessibility + motion notes** — Dynamic Type, contrast pairs, 44pt, Reduce-Motion,
   and how "Featured" stays honest *and* on-brand.
7. **The spec board** for tokens/components — but the screens must look like a **real,
   modern, exciting app**, not a catalog.
