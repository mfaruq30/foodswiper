# Claude Design Prompt — Final Deliverable (Phase 8)

> **What this is.** A self-contained design brief for a *fresh* Claude (or
> Claude Design) session with no memory of this build. It describes the Munch
> iOS app **exactly as it ships today** — every token, component, screen, and
> state — and asks for an elevated visual system on top. Written **last** (spec
> §14), after every screen exists, so it documents what was actually built, not
> what was planned. Paste everything below the line into a new session.
>
> **Ground truth, verified.** All literal values below were read directly from
> `ios/Munch/Munch/DesignSystem/Theme.swift`, `Components.swift`, `CardArt.swift`,
> and the eight feature screens. The placeholder fork app icon (`tools/make_app_icon.py`)
> is intentionally a stand-in — **producing its replacement is part of this brief.**

---

## ROLE & CONTEXT

You are a senior product designer shaping the visual identity of **Munch**, a
swipe-based restaurant-discovery iPhone app for New York City and Boston. The
user sets what they're craving, then swipes through *real* nearby restaurants
(Tinder-style) until they match on one to eat at. Think "Tinder for restaurants,"
but warm and editorial rather than slick and cold.

The app is **already built and functional** in SwiftUI (iOS 17+, iPhone-only,
light-mode-first). It has a real, coherent design system — your job is **not** to
invent from scratch but to **elevate what exists**: refine the visual language,
tighten the art direction, and design the few things that are still placeholders
(most importantly the **cuisine card-art system**, which is the product's primary
visual identity). Everything you produce must stay **SwiftUI-implementable** and
respect the existing token names so an engineer can apply it without rewrites.

### Aesthetic North Star
Warm, editorial, appetite-forward, human. Off-white "paper" canvas (never stark
white), a confident warm-orange accent, and an editorial serif (Fraunces) for
display type against a clean SF Pro body. The feeling: a beautifully printed
neighborhood food zine, not a delivery-app spreadsheet.

### Hard constraints (non-negotiable)
1. **SwiftUI-implementable on iOS 17.** No effects that can't be built with
   SwiftUI primitives (gradients, shapes, `.shadow`, SF Symbols, blend modes are fine).
2. **Light mode first.** No dark-mode variants are defined yet; if you propose
   one, keep it additive and secondary.
3. **Accessibility is a gate, not a nicety:** Dynamic Type must scale (don't
   hardcode pixel type that breaks large sizes), all tap targets ≥ **44pt**, and
   text/background pairs must meet WCAG AA contrast. Every control already carries
   a VoiceOver label and a stable `accessibilityIdentifier` — preserve them.
4. **Honest "Featured" treatment.** If a card is sponsored/paid placement it must
   carry a *visible* "Featured"/"Sponsored" label. Never design a treatment that
   disguises paid placement as an organic result. (This is also a Terms commitment.)
5. **Reuse the token names.** Map every value you choose to the existing
   `Theme.*` tokens below (or propose a *named* new token); no magic numbers.
6. **Data honesty.** Match percentages come from *Munch users' swipes*, never
   scraped third-party ratings. Don't design UI implying Yelp/Google-style review
   data — it doesn't exist and won't.

### What to deliver
- A refined **design-token sheet** (you may adjust values, but keep the token
  names and the warm-editorial intent; justify any change).
- The full **component kit**, visually specified (states included).
- **The cuisine card-art system** as a first-class deliverable — see its section.
- Each **screen** redrawn with all states (empty / loading / error / success).
- A new **app icon** concept consistent with the system (replacing the placeholder).
- Notes on **motion** (the swipe + match moments especially).

---

## DESIGN TOKENS (as shipped — the exact current values)

Light-mode-first. Colors are sRGB hex; the app builds them via a `Color(hex:)`
helper. Spacing is a 4pt base scale. Display type is Fraunces (SIL OFL, bundled),
body type is the native SF Pro stack (for Dynamic Type).

### Color palette
| Token | Hex | Role |
|---|---|---|
| `Theme.paper` | `#FAF6F0` | App background — warm off-white "paper" (never pure white) |
| `Theme.surface` | `#FFFDF9` | Card / row surface — a half-step brighter than paper, for lift |
| `Theme.ink` | `#2B2118` | Primary text (display + body) — warm near-black |
| `Theme.inkSecondary` | `#6E5F51` | Secondary text — captions, metadata |
| `Theme.accent` | `#E8552E` | Brand warm-orange — CTAs, selection, brand moments |
| `Theme.accentSoft` | `#FBE3DB` | Soft accent tint — chips, selected states, callouts |
| `Theme.yes` | `#2E8B57` | "Yes" / right-swipe affirmation (green) |
| `Theme.nope` | `#C0392B` | "Nope" / left-swipe + destructive (red) |
| `Theme.stroke` | `#E8DFD3` | Hairlines, card borders, disabled fills (warm neutral) |

### Type scale
Display = **Fraunces** (SIL OFL, bundled), via `Theme.display(size)`, which falls
back to system **serif `.semibold`** if the font fails to register (the UI never
blanks). Body and smaller roles use native `.system` SF Pro for Dynamic Type.

| Token | Font | Size | Use |
|---|---|---|---|
| `Theme.munchTitle` | Fraunces (display) | 34pt | Large editorial headline ("It's a match", brand) |
| `Theme.munchHeading` | Fraunces (display) | 24pt | Section headings, screen titles |
| `Theme.munchCardName` | Fraunces (display) | 28pt | Restaurant name on a card |
| `Theme.display(_:)` | Fraunces (display) | parametric | Any other display size (e.g. the 22pt deck wordmark) |
| (system) | SF Pro | `.headline`/`.subheadline`/`.body`/`.footnote`/`.caption`/`.caption2` | All body/meta/control text |

### Spacing (4pt base)
`space2` = 4 · `space3` = 8 · `space4` = 12 · `space5` = 16 · `space6` = 24 ·
`space7` = 32 · `space8` = 48. These are the *only* approved spacings.

### Radii
`radiusCard` = **24pt** (cards) · `radiusControl` = **14pt** (buttons, chips-as-rounded-rect,
callouts, alternates) · `radiusChip` = **999pt** (full capsule / pills).

### Elevation
One shadow token, applied wherever a card lifts off paper:
`Theme.cardShadow` = color `ink` @ **10% opacity**, radius **18**, offset **x:0, y:8**.
No other shadow is defined — keep elevation singular and restrained.

### Motion (today)
There are no centralized motion tokens; motion lives in the swipe interaction
(below): card fly-off **0.25s**, a rotation tied to drag, and YES/NOPE stamps
that fade in with drag distance. Treat tasteful, physical, spring-y motion on the
swipe + match moments as in-scope to specify.

---

## COMPONENT KIT (as shipped)

All controls enforce ≥44pt targets, VoiceOver labels, and Dynamic Type. Specify
each component's full visual treatment and **every state**.

- **PrimaryButton** — brand CTA. Props: `title`, `enabled` (default true), `action`.
  Enabled: `accent` fill, white `.headline` text. Disabled: `stroke` fill,
  `inkSecondary` text. `maxWidth: .infinity`, `minHeight: 54`, `radiusControl`.
- **SecondaryButton** — outline, lower weight. `ink` text, no fill,
  `stroke` border 1.5pt, `radiusControl`, `maxWidth: .infinity`, `minHeight: 54`.
- **SelectableChip** — toggle for cuisine/dietary multi-select. Props: `label`,
  `emoji?`, `selected`, `action`. Selected: `accentSoft` fill, `accent` text,
  `accent` border. Default: `surface` fill, `ink` text, `stroke` border (1.5pt).
  Capsule, `.subheadline.weight(.medium)`, `minHeight: 44`.
- **ProgressDots** — onboarding step indicator. Props: `total`, `current`.
  Inactive 8×8pt `stroke` capsules; active dot 22×8pt `accent`. Label "Step N of M".
- **ReasonChip** — *signature moment*. The AI/heuristic reason a venue matches.
  `sparkles` SF Symbol + `.footnote.weight(.medium)` text (max 2 lines), `accentSoft`
  fill, `accent` text, `radiusControl`. Label "Why this match: …".
- **PriceLabel** — `$`×tier (clamped 1–4) + `?` suffix when the tier was *imputed*
  (estimated). `.subheadline.weight(.semibold)`, `inkSecondary`. Honestly signals
  estimated prices — keep that legible, don't hide the `?`.
- **StateMessage** — full-screen empty/error/loading. Props: `icon` (SF Symbol),
  `title`, `detail`, optional `retryTitle` + `retry`. Centered VStack, icon
  `.system(size: 44)` `inkSecondary`, title `munchHeading` `ink`, detail `.body`
  `inkSecondary`, optional PrimaryButton retry.

---

## CUISINE CARD-ART SYSTEM (first-class deliverable)

**This is the product's visual identity.** Open restaurant data has ~**0.04%**
real photo coverage, so cards do **not** show photos — they show a deterministic,
cuisine-keyed **gradient + emoji** composition. This is the primary art direction
of the whole app, not a fallback. Today's implementation (your starting point):

- **Deterministic & stable:** a venue's `id` hash picks one of **two** gradient
  variants for its cuisine family, so the same venue always looks identical and
  adjacent same-cuisine cards don't look cloned.
- **Composition:** `CardArt(venueId, cuisine)` = a `LinearGradient`
  (`.topLeading → .bottomTrailing`) under a single large centered **emoji**
  (96pt, ~0.9 opacity). Art fills the top **~46%** of the card.
- **Gradient families (current `(start → end)` pairs):**
  - *Pizza / Italian / Mediterranean:* `#F2A65A→#E8552E`, `#F7C59F→#D7263D`
  - *Asian (japanese, sushi, ramen, korean, chinese, pan-asian, noodles, vietnamese, thai, filipino):* `#F67B45→#9B2226`, `#FFB385→#BC4749`
  - *Latin (mexican, latin, caribbean, peruvian, spanish):* `#F9C74F→#F3722C`, `#F8961E→#D62828`
  - *Plant-based (vegan, vegetarian, salad, juice):* `#B5C99A→#55828B`, `#CFE1B9→#718355`
  - *Sweet / brunch (coffee, bakery, dessert, breakfast, bagel, bubble tea):* `#E6CCB2→#9C6644`, `#F1DCA7→#B08968`
  - *Seafood:* `#90C2E7→#3E7CB1`, `#A9D6E5→#2A6F97`
  - *Default (unmapped):* `#F2A65A→#BC6C25`, `#F7B267→#99582A`
- **Cuisine → emoji** is a fixed catalog. The 16 onboarding cuisines:
  🍕 pizza · 🍝 italian · 🥡 chinese · 🍱 japanese · 🍣 sushi · 🍜 ramen ·
  🍚 korean · 🥘 thai · 🌮 mexican · 🍔 burger · 🥪 american · 🍛 indian ·
  🫒 mediterranean · 🧆 middle_eastern · 🦞 seafood · 🍰 dessert. (Plus ~35 more
  in the extended catalog; unknown cuisines fall back to 🍽️.)

**Your task here:** elevate this into a polished, ownable art system. Keep it
deterministic, cuisine-coherent, SwiftUI-buildable, and appetite-forward. You may
move beyond flat two-stop gradients (e.g. layered gradients, soft grain, abstract
food-form shapes, a refined glyph treatment instead of raw emoji) — but it must
degrade gracefully, stay legible behind the card's text overlay, and read
beautifully at a glance in a fast-swiping deck. Define the families, the variant
logic, and the glyph/illustration direction.

---

## SCREEN INVENTORY (every screen, every state)

The app's flow: **Sign In → Onboarding (Welcome → Cuisines → Anchors → Mode) →
Main tabs (Swipe deck, Profile)**, with the Match sheet over the deck and Legal /
Data-sources pages off Profile.

### 1. Sign In (auth gate)
Shown only to new users / after sign-out (demo mode skips it; returning users
auto-sign-in). Centered: "Munch" wordmark (`munchTitle`, accent) · tagline
**"Stop deciding. Start eating."** (`inkSecondary`) · a large 🍜 (64pt) · the
**Sign in with Apple** button (Apple's black style, 54pt tall) · legal line
**"By continuing you agree to our Terms and Privacy Policy."** (caption2).
States: **idle** · **loading** (button → spinner) · **error** (button returns,
red `nope` message: "Apple sign-in didn't return a token…", "Couldn't sign in…",
or "Couldn't complete sign-in…"); a *user-cancelled* sign-in shows **no** error.

### 2. Onboarding — chrome
Linear 4 steps with a top bar (back button + ProgressDots on steps 2–4) and
right-to-left slide+fade transitions between steps.

**2a. Welcome** — decorative emoji row 🍜 🌮 🍕 · "Munch" (`munchTitle`, accent) ·
tagline · **"Get started"** PrimaryButton · helper **"About 90 seconds to set up."**
Single state.

**2b. Cuisines (gate: pick ≥ 5)** — heading **"What do you crave?"**, instruction
**"Pick at least 5."**, a 2-column grid of SelectableChips (emoji + label), a live
counter **"{N} of 5 picked"** (turns `accent` when satisfied), and a Continue
PrimaryButton disabled until 5 are chosen.

**2c. Anchors (optional, high-signal)** — heading **"Name a few favorites"**, sub
**"Restaurants you already love teach Munch your taste. This is the secret sauce."**
A **Home metro** segmented picker, a pill-shaped search field (magnifier icon,
1.5pt border, placeholder "Search restaurants"), and a results area. States:
**idle** (query < 2 chars → nothing) · **loading** (accent spinner) · **results**
(≤ 8 rows: name semibold, cuisines joined by " · " in caption gray, `plus.circle`
→ `checkmark.circle.fill` accent when picked; picked rows get `accentSoft` bg +
accent border) · **no matches** ("No matches — try another spelling."). Picked
anchors (≤ 5) show as a horizontal chip strip with caption "Picked — tap to
remove" (or "…that's the max of 5. Tap to remove." at the limit). Footer
"Optional — but even one helps a lot." + Continue (never blocks).

**2d. Mode** — heading **"How are you eating?"**, three ModeCards (emoji 40pt +
name `.headline` + caption; selected = `accent` bg/checkmark/title, unselected =
`surface` bg + `stroke` border; ≥60pt tall pill): 🍽️ **Dine in** "Table for now",
🥡 **Pickup** "Grab and go", 🛵 **Delivery** "To your door". Submit
**"Start swiping"**. States: **ready** · **submitting** (spinner) · **error**
(red "Couldn't save — is the demo server running?").

### 3. Swipe deck (the core screen)
Top: **"Munch"** wordmark (`display(22)`) + three **ModeTabs** (all-caps Dine In /
Pickup / Delivery; selected = `accent` fill + white text + accent border 1.5pt;
unselected = `surface` + `ink` + `stroke` border; `.subheadline.weight(.semibold)`,
44pt targets). Optional **fallback-location banner** ("Using {metro} center —
enable location for nearby picks", footnote `inkSecondary`) — honest, never a
silent fake fix.

**SwipeCardStack:** the top **3** cards visible, staggered (each deeper card
scaled −0.05 and offset +10pt in Y). The **front card** (`SwipeCardView`):
- Top **~46%** is `CardArt` (gradient + emoji, above).
- Body: restaurant **name** (`munchCardName`), a meta row — cuisine, `PriceLabel`,
  and **distance** (with a `location.fill` glyph) — and the **ReasonChip**.
- A **"DISCOVER"** badge (`.caption2` bold) marks an exploration card (the
  algorithm deliberately showing something outside the user's usual taste).
- Card: `surface`, `radiusCard` (24pt), 1pt `stroke` border, `cardShadow`.
- **Sponsored cards must show a visible "Featured" label** (design this honestly).

**Swipe gesture & feedback:** drag rotates the card and fades in a stamp —
**"YES"** (`yes` green) dragging right, **"NOPE"** (`nope` red) dragging left
(32pt, 3pt stroke, ~12° rotation). Past threshold the card flies off (~600pt) over
**0.25s**. Two circular **56pt** buttons below mirror the gesture: **Pass**
(`xmark`, `nope`) and **Like** (`heart.fill`, `yes`), each `surface` + 1.5pt
`stroke` border, ids `swipe-nope` / `swipe-yes`.

**Deck states:** **loading** (large accent ProgressView, controls hidden — never
flashes empty) · **error** (StateMessage `wifi.exclamationmark`, "Connection
trouble", retry "Try again") · **empty—dietary** (`fork.knife`, "Nothing matches
your filters here", "Try widening your search or relaxing dietary filters.", no
retry) · **empty—exhausted** (`sparkles`, "That's everyone nearby", "Check back
soon — or switch modes.", no retry) · **active** (stack + controls).

### 4. Match sheet ("It's a match")
A modal sheet, presented at most once per session after a qualifying right-swipe.
Hero: `sparkles` (accent) + **"It's a match"** (`munchTitle`), the matched venue
as a non-interactive 320pt `SwipeCardView`, and the reason line (`.headline`,
accent, centered). **Mode-specific CTAs** (each logs a conversion *before*
opening the outbound link): Dine-In → **"Directions"** (Apple Maps) + **"Call"**
(if phone known); Pickup → **"Find on DoorDash"**; Delivery → **"Find on
DoorDash"** + **"Find on Uber Eats"**. Then an **"Also great"** section (up to 2
non-interactive alternate rows: cuisine emoji, name semibold, "cuisine · distance"
footnote, `surface` + `stroke`, `radiusControl`) and a **"Keep swiping"**
SecondaryButton that dismisses. Background `paper`.

### 5. Profile
`.insetGrouped` List on `paper`, `surface` rows. Sections:
- **Your taste** — read-only `accentSoft`/`accent` capsule chips (emoji + cuisine)
  of the user's anchor cuisines; empty → "Pick favorites during onboarding".
- **Dietary** — 4 SelectableChips (Vegetarian, Vegan, Gluten-free, Halal); tapping
  toggles optimistically and saves, reverting with an alert on failure. Footer
  explains coverage is sparse (OSM tags) and to relax filters if decks come up empty.
- **About** — NavigationLinks: "Privacy Policy", "Terms of Service", "Data sources
  & attribution".
- **Account** — "Home metro" (display value or "Not set"); **"Delete my account"**
  (`.destructive`, `nope`). Delete → confirmation dialog ("This permanently
  deletes your profile and swipe history." / "Delete everything" / "Cancel") →
  inline "Deleting your account…" spinner → routes back to onboarding. Errors
  show a "Something went wrong" alert.
- **Footnote** — centered ODbL credit link "Munch demo • data © OpenStreetMap
  contributors". States: **loading** ("Loading your profile…") · **error**
  (StateMessage `person.crop.circle.badge.exclamationmark`, "Couldn't load your
  profile", retry) · **loaded**.

### 6. Legal & Data-sources pages
Both: `ScrollView` on `paper`, `munchHeading` title, `space6` rhythm, inline nav
title. **LegalView** (Privacy / Terms) opens with an `accentSoft` callout
**"Plain-English summary — the full legal text ships with public launch."** then
headed sections. **DataSourcesView** carries the required attributions —
**© OpenStreetMap contributors** with a working `openstreetmap.org/copyright`
link (ODbL), NYC Open Data (DOHMH), Analyze Boston (PDDL) — and an `accentSoft`
honesty note: **"Munch's match percentages come from Munch users, never scraped
ratings."**

---

## DELIVERABLE CHECKLIST (what to hand back)

1. **Refined token sheet** — final palette, type scale, spacing, radii, elevation,
   and explicit **motion** specs; keep token *names*, justify any value changes.
2. **Component kit** — each component above, all states, in the refined system.
3. **Cuisine card-art system** — families, variant logic, glyph/illustration
   direction; legible behind text, beautiful at a glance, deterministic.
4. **Every screen** above, all states, in the refined system (light mode).
5. **App icon** concept replacing the placeholder fork, consistent with the system.
6. **Accessibility notes** — Dynamic Type behavior, contrast pairs, 44pt targets,
   and how the "Featured"/sponsored treatment stays honest *and* on-brand.

Keep it warm, editorial, appetite-forward — and buildable in SwiftUI tomorrow.
