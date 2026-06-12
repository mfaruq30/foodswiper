// In-app plain-English legal summaries. The repo drafts (legal/*.md) are
// Phase-0 skeletons, so what ships here must stay truthful to what the app
// actually does — each screen carries the "summary, full text at public
// launch" caveat instead of pretending to be attorney-reviewed prose.

import SwiftUI

/// Which document the screen renders.
enum LegalDocument {
    case privacy
    case terms
}

struct LegalView: View {
    let document: LegalDocument

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.space6) {
                Text(title)
                    .font(.munchHeading)
                    .foregroundStyle(Theme.ink)

                summaryNote

                ForEach(sections) { section in
                    VStack(alignment: .leading, spacing: Theme.space3) {
                        Text(section.heading)
                            .font(.headline)
                            .foregroundStyle(Theme.ink)
                        Text(section.text)
                            .font(.body)
                            .foregroundStyle(Theme.ink)
                    }
                }
            }
            .padding(Theme.space6)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(Theme.paper)
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
    }

    // MARK: - Document selection

    private var title: String {
        switch document {
        case .privacy: "Privacy Policy"
        case .terms: "Terms of Service"
        }
    }

    private var sections: [LegalSection] {
        switch document {
        case .privacy: Self.privacySections
        case .terms: Self.termsSections
        }
    }

    /// Honest framing: these are summaries, not the binding text.
    private var summaryNote: some View {
        Text("Plain-English summary — the full legal text ships with public launch.")
            .font(.footnote.weight(.medium))
            .foregroundStyle(Theme.accent)
            .padding(Theme.space4)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.accentSoft)
            .clipShape(RoundedRectangle(cornerRadius: Theme.radiusControl))
    }

    // MARK: - Privacy (summarizes legal/privacy-policy.md)

    // swiftformat:disable indent -- string interiors are content, not code
    private static let privacySections: [LegalSection] = [
        LegalSection(
            heading: "What we collect",
            text: """
                Account basics — your name and the email your Apple ID chooses to \
                share — plus your location while you browse decks, your food \
                preferences, and your swipe and tap-through history.
                """
        ),
        LegalSection(
            heading: "Why we collect it",
            text: """
                To personalize your decks. Your swipes train the recommendation \
                model that decides which restaurants you see next and why.
                """
        ),
        LegalSection(
            heading: "Who else sees it",
            text: """
                Munch runs on a cloud hosting provider (Google Firebase) for \
                storage and sign-in. The per-card reasons are written by an AI service \
                (Anthropic) that receives only a compact, non-identifying taste \
                profile — never your name, email, or account identifiers. Tapping \
                directions or order hands you off to Apple Maps, DoorDash, or \
                Uber Eats, and their own policies apply from there. No Google, \
                Yelp, or Beli data is collected, scraped, or shared.
                """
        ),
        LegalSection(
            heading: "Where restaurant data comes from",
            text: """
                Open sources: OpenStreetMap contributors, NYC Open Data, and \
                Analyze Boston. Full credits live in the Data sources screen.
                """
        ),
        LegalSection(
            heading: "Retention and deletion",
            text: """
                We keep your data only while your account exists. Delete your \
                account any time from Profile → Delete my account — that removes \
                your profile and swipe history from our servers, right from the \
                app, no email required.
                """
        ),
        LegalSection(
            heading: "Age",
            text: """
                Munch is rated for ages 13 and up and is not directed at children \
                under 13.
                """
        ),
        LegalSection(
            heading: "Contact",
            text: """
                A privacy contact address will be published with the public \
                launch alongside the full policy.
                """
        ),
    ]

    // MARK: - Terms (summarizes legal/terms-of-service.md)

    private static let termsSections: [LegalSection] = [
        LegalSection(
            heading: "A discovery tool, not the restaurant",
            text: """
                Munch helps you decide where to eat. We don't prepare meals, take \
                orders, deliver food, or set prices — your meal, order, and \
                payment are between you and the restaurant or delivery service.
                """
        ),
        LegalSection(
            heading: "Results are best-effort",
            text: """
                Match percentages and reasons are suggestions, not guarantees. \
                Restaurant details come from open data that refreshes regularly \
                but can still be stale — always confirm hours, menus, prices, and \
                especially allergen handling with the restaurant itself.
                """
        ),
        LegalSection(
            heading: "Sponsored cards are labeled",
            text: """
                If a restaurant ever pays for placement, its card carries a \
                visible sponsored label. Unlabeled cards are never paid.
                """
        ),
        LegalSection(
            heading: "Deep links leave Munch",
            text: """
                Directions and order buttons open Apple Maps, DoorDash, or \
                Uber Eats. Once you leave Munch, those services' own terms apply.
                """
        ),
        LegalSection(
            heading: "Liability and governing law",
            text: """
                Limitation-of-liability and governing-law terms will be finalized \
                with counsel for the public launch. The demo is provided as-is, \
                to the fullest extent allowed by law.
                """
        ),
    ]
    // swiftformat:enable indent
}

// MARK: - Supporting model

/// One heading + body block of a rendered document.
private struct LegalSection: Identifiable {
    let heading: String
    let text: String
    var id: String { heading }
}
