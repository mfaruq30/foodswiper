# Munch — App Store Connect Submission Artifacts

Documentation for the TestFlight submission (Phase 6). Munch is a swipe-based
restaurant discovery app, iOS 17+, SwiftUI, iPhone-only (`TARGETED_DEVICE_FAMILY = 1`).

Ground-truth sources this doc is reconciled against:
- `ios/Munch/Munch/Resources/PrivacyInfo.xcprivacy` — the shipped privacy manifest
- `legal/privacy-policy.md` — the hosted privacy policy
- `ios/Munch/project.yml` — Info.plist usage strings
- `docs/DECISIONS.md` — D-003, D-004, D-010, D-013, D-014, D-019

> **Single source of truth rule:** the App Privacy answers below, the privacy
> manifest, and the privacy policy MUST stay byte-for-byte consistent in meaning.
> A mismatch between any two is a documented App Store rejection reason
> (`PrivacyInfo.xcprivacy` header comment + D-014 context).

---

## 1. App Privacy "nutrition label" answers (App Store Connect questionnaire)

These are the exact answers to enter in App Store Connect → App Privacy. Each
maps 1:1 to a `NSPrivacyCollectedDataType` entry in `PrivacyInfo.xcprivacy`.
Nothing is collected that is not in the manifest, and nothing in the manifest is
omitted here.

### Data type 1 — Precise Location
- Manifest entry: `NSPrivacyCollectedDataTypePreciseLocation`
- **Collected?** Yes
- **Linked to the user's identity?** Yes (`...Linked = true`)
- **Used for tracking?** No (`...Tracking = false`)
- **Purposes:** App Functionality only (`...PurposeAppFunctionality`)
- App Store Connect mapping: Location → **Precise Location** → used for "App
  Functionality"; "Yes, data is linked to the user's identity"; "No, not used
  for tracking."
- Honest why: used solely at search time to find restaurants near you. Matches
  `NSLocationWhenInUseUsageDescription` ("Munch uses your location to find
  restaurants near you.").

### Data type 2 — Other Usage Data (swipe / conversion history)
- Manifest entry: `NSPrivacyCollectedDataTypeOtherUsageData`
- **Collected?** Yes
- **Linked to the user's identity?** Yes (`...Linked = true`)
- **Used for tracking?** No (`...Tracking = false`)
- **Purposes:** App Functionality **and** Analytics
  (`...PurposeAppFunctionality`, `...PurposeAnalytics`)
- App Store Connect mapping: Usage Data → **Other Usage Data** → used for both
  "App Functionality" and "Analytics"; "Yes, linked to identity"; "No tracking."
- Honest why: which cards you swipe (and which way) plus outbound conversion
  taps. App Functionality = personalizes your deck; Analytics = trains/improves
  the recommendation model for all users (disclosed in the privacy policy:
  "your swipe and conversion history is used to train…"). This dual purpose is
  the one nuance reviewers will check against the manifest — both flags are
  present in both places.

### Data type 3 — User ID
- Manifest entry: `NSPrivacyCollectedDataTypeUserID`
- **Collected?** Yes
- **Linked to the user's identity?** Yes (`...Linked = true`)
- **Used for tracking?** No (`...Tracking = false`)
- **Purposes:** App Functionality only (`...PurposeAppFunctionality`)
- App Store Connect mapping: Identifiers → **User ID** → "App Functionality";
  "Yes, linked"; "No tracking."
- Honest why: the device-generated demo identity / auth user id that ties a
  user's data to their account and syncs across sessions.

### Tracking section
- **Does this app use data for tracking?** **No.** No `NSPrivacyTrackingDomains`
  are declared and `NSPrivacyTracking = false`. Therefore **no ATT (App Tracking
  Transparency) prompt** is required or shown. Do not enable the "Used to Track
  You" toggle for any data type.

### Three places that MUST agree (keep in sync on every change)
1. `ios/Munch/Munch/Resources/PrivacyInfo.xcprivacy` (the shipped manifest)
2. App Store Connect → App Privacy answers (this section)
3. `legal/privacy-policy.md` (hosted at the web/ Privacy Policy URL)

Any edit to one requires re-checking the other two before the next upload.

---

## 2. PrivacyInfo.xcprivacy audit

Read against the current shipped file. Confirmed:

- **`NSPrivacyTracking = false`** ✓ — no tracking. Consequence: no ATT prompt,
  and `NSPrivacyTrackingDomains` is an empty array (correct — a non-empty
  domains list with tracking false would be invalid).
- **`NSPrivacyTrackingDomains = []`** ✓ — no domains classified as tracking.
- **Every `NSPrivacyCollectedDataType` carries purpose flags** ✓:
  - Precise Location → `[AppFunctionality]`
  - Other Usage Data → `[AppFunctionality, Analytics]`
  - User ID → `[AppFunctionality]`
  - All three: `...Linked = true`, `...Tracking = false`.
- **Required-reason API declaration present** ✓ — `NSPrivacyAccessedAPITypes`
  declares `NSPrivacyAccessedAPICategoryUserDefaults` with reason **`CA92.1`**
  (UserDefaults accessed only by the app itself, for onboarding state +
  preferred mode). This is the correct reason code for first-party-only
  UserDefaults access.

**No issues found.** The manifest is valid and internally consistent, and its
declarations match Section 1.

### Pending item (flag for re-audit) — Sign in with Apple / Firebase Auth SDK
Sign in with Apple via the **Firebase Auth SDK is not yet integrated** (the only
auth code today is `DemoAuthProvider.swift`, the dev-auth shim). It is pending a
decision. **When/if FirebaseAuth is added:**
- The Firebase Auth SDK ships its **own** `PrivacyInfo.xcprivacy` (bundled
  inside the SPM product). That manifest is aggregated into the app's privacy
  report at build time.
- It declares its own collected data types / required-reason APIs. The combined
  privacy report MUST be re-audited and any newly surfaced data type reconciled
  back into Section 1 and the privacy policy (the three-places rule).
- Sign in with Apple also triggers D-013 obligations (Apple token revocation on
  account deletion, TN3194) — already designed for, but verify the live path at
  integration time.

---

## 3. SPM dependency privacy audit

**Current state — one dependency, no privacy impact.**

- The app target depends on exactly one SwiftPM package: the **local first-party
  `MunchKit`** package (`ios/Munch/Munch/Packages/MunchKit`, referenced via
  `path:` in `project.yml`).
- `MunchKit/Package.swift` declares **no external dependencies** — it is pure
  domain logic (scoring helpers, gesture-commit math, domain models), builds and
  tests on Linux/Windows, and imports no SwiftUI/UIKit.
- It accesses **no privacy-impacting / required-reason APIs** and collects no
  data, so it **does not need and does not ship its own privacy manifest**. As a
  first-party package compiled from source, its (absent) declarations are
  covered by the app-target `PrivacyInfo.xcprivacy`.
- **No other third-party SPM dependencies exist** in the project today.

**Pending — FirebaseAuth (if added for Sign in with Apple):** recent Firebase
SDK releases ship a per-product `PrivacyInfo.xcprivacy` (privacy manifest)
inside each SPM target. At integration time, **verify the manifest is present**
in the resolved FirebaseAuth product and fold its declarations into Sections 1
and 2. Do not assume an older Firebase version (some predate bundled manifests)
— pin a version that ships one.

---

## 4. App Store review notes (paste into "Notes for Review")

> **Munch** is a swipe-based restaurant discovery app: you set your cravings,
> then swipe through nearby real restaurants (seeded from OpenStreetMap and city
> open data) until you match on one to eat at.
>
> **Location:** Munch requests "When In Use" location only to find restaurants
> near you (this is the exact purpose shown in the permission prompt). Declining
> location is fully supported — the app falls back to a metro center and you can
> search by area instead. No location is sold or used for tracking.
>
> **Sign in with Apple:** the app uses Sign in with Apple for authentication.
> **No separate test credentials are required** — tap "Sign in with Apple" and
> the account is created on first sign-in; the full flow (onboarding → swipe
> deck → match) is then reachable immediately. Account deletion ("Delete my
> account" in the Profile tab) purges all user data and revokes the Apple token.
>
> _If a dedicated review account is preferred instead:_
> - Username: `<PLACEHOLDER — add if a non-Apple test login is provisioned>`
> - Password: `<PLACEHOLDER>`
>
> **Third-party hand-off:** tapping "Directions" / "Order" / "Call" on a matched
> restaurant opens a third-party app (Apple Maps, a delivery search URL, or the
> phone dialer). These are honest outbound deep links; Munch does not process
> orders or payments in-app.

> Note for the submitter: if Sign in with Apple is **not** wired by submission
> time and the build still uses dev-auth, replace the "Sign in with Apple"
> paragraph with the actual entry path and fill in the placeholder test account.

---

## 5. Age rating

- **Rating: 13+** under Apple's current age-tier system (13+/16+/18+, which
  replaced the legacy 12+/17+ tiers as of July 2025). See **D-014**.
- **The deciding questionnaire answer:** the **alcohol reference** question.
  Restaurants surfaced in the deck **can be alcohol-serving venues** (bars,
  gastropubs), so answer the "References to / depictions of alcohol" question
  **honestly = Infrequent/Mild** rather than None. This is what lands the rating
  at 13+ rather than 4+.
- **No user-generated content:** Munch has no reviews, comments, chat, or
  user-submitted media — the catalog is curated open data. So the UGC /
  moderation questions are answered **No**, and there is nothing to moderate.
- **DSA trader status:** App Store Connect requires a **Digital Services Act
  trader-status declaration** (Business → trader status) **even for US-only
  distribution** — it must be completed or the app cannot be submitted /
  distributed. Declare trader status for Manaa/Munch accordingly before submit.

---

## 6. Screenshots plan

Apple requires, at minimum, screenshot sets for **6.7-inch** and **6.1-inch**
iPhone displays. (iPhone-only app, so no iPad sets needed.)

**Plan (to be executed — these are not yet captured; no `.xcassets`/screenshots
exist in the repo today):**
- **Capture source:** the iOS simulator. The **`ios-e2e` CI lane already drives
  the full onboarding → deck → match flow** on a booted simulator; extend it to
  call `xcrun simctl io <udid> screenshot` (or UI-test `XCUIScreenshot`) at each
  key screen and upload the PNGs as workflow artifacts. This keeps screenshots
  reproducible on a Windows dev machine (no local Mac needed, per D-001).
- **Five key screens to capture:**
  1. **Welcome** — "Stop deciding. Start eating."
  2. **Cuisine grid** — the cravings picker (Cravings step)
  3. **Swipe deck** — a real restaurant card with its reason line (+ DISCOVER badge)
  4. **Match** — the "It's a match" moment with Directions / Call / order CTAs
  5. **Profile** — taste, dietary filters, legal links, Delete my account
- Run the capture on both a 6.7" and a 6.1" simulator device to produce both
  required sets.

---

## 7. §9 TestFlight readiness checklist (Phase 6)

Current status of each Phase-6 gate item. Legend: ✅ done · ⛔ blocked-on-user ·
🟡 pending (engineering work remaining).

- [ ] 🟡 **`xcodebuild archive` succeeds** — archive/signing config not yet set;
      `project.yml` notes `DEVELOPMENT_TEAM` + manual signing are a FUTURE(Phase 6)
      item. Blocked partly on the paid Apple team (D-003).
- [ ] 🟡 **Runs on iOS 17 simulator + device** — simulator E2E is green via the
      `ios-e2e` lane; on-device run needs the Apple Developer account /
      provisioning (⛔ depends on enrollment).
- [ ] 🟡 **Sign in with Apple works end-to-end** — not yet wired; only
      `DemoAuthProvider` (dev auth) exists. Pending the FirebaseAuth/SIWA
      decision; requires the paid team for the SIWA entitlement (D-003).
- [ ] 🟡 **Account deletion purges data (+ Apple token revoke, D-013)** — delete
      flow exists in the demo (Profile → Delete my account); the Apple
      `/auth/revoke` call lands with real SIWA, so end-to-end is pending SIWA.
- [x] ✅ **`PrivacyInfo.xcprivacy` valid + consistent** — audited (Section 2);
      consistent with App Privacy answers and the privacy policy.
- [x] ✅ **SPM deps audited** — only first-party `MunchKit`, no manifest needed
      (Section 3). Re-audit gate flagged for FirebaseAuth if added.
- [ ] 🟡 **App icon (all sizes) + launch screen + screenshots** — launch screen
      configured (`UILaunchScreen` in `project.yml`); **no `.xcassets`/AppIcon
      asset set exists yet**, and screenshots are planned but not captured
      (Section 6). ⛔ needs the icon artwork from the user.
- [x] ✅ **Legal docs reachable in-app + hosted** — `legal/privacy-policy.md`,
      `terms-of-service.md`, `eula.md` exist; reachable from the Profile tab
      (Privacy/Terms/Data sources) and hosted via `web/` (D-016 GitHub Pages).
      ⛔ Confirm the live Pages URLs resolve before submit.
- [ ] 🟡 **Reco service deployed + reachable** — runs locally / in CI (memory
      backend); the production Cloud Run deploy (D-002/D-019) needs Firebase
      project + secrets wiring. ⛔ depends on user's Firebase/Cloud Run setup.
- [ ] 🟡 **`make verify` green** — `verify` target exists; confirm a green run on
      the submission commit (re-run gate).
- [ ] 🟡 **Eval shows learned > baseline** — **by design this stays as-is for
      v1**: the heuristic is the champion; the learned ranker beats baseline only
      on *synthetic* data and is NOT promoted (D-007/D-023). Real-swipe promotion
      is post-launch. Mark satisfied as "heuristic champion + challenger gated",
      not "learned serving."
- [x] ✅ **RUNBOOK covers deploy / secrets / seed / rotation** —
      `docs/RUNBOOK.md` has Deploy, Secrets, Seed/re-sync, and operational
      landmine sections.
- [x] ✅ **Review notes drafted** — Section 4 above.

---

### Blocked-on-user vs done — quick read
- **Done (✅):** privacy manifest audit, SPM audit, legal docs present, RUNBOOK,
  review notes drafted, eval posture (heuristic champion is the intended v1 state).
- **Blocked on user (⛔):** Apple Developer enrollment / signing team, on-device
  run, SIWA entitlement, app icon artwork, Firebase/Cloud Run production deploy +
  secrets, confirming hosted legal URLs resolve.
- **Pending engineering (🟡):** wire Sign in with Apple (+ live account-deletion
  revoke), archive config, capture screenshots, confirm `make verify` green on
  the release commit.
