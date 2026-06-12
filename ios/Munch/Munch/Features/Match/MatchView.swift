// The celebration sheet (spec §4.3): swiping pauses and the best right-swipe
// is presented with confidence. Every outbound CTA logs its conversion BEFORE
// opening the URL — conversions are the product's success metric, and the
// handoff app may never give us control back.

import MunchKit
import SwiftUI
import UIKit

/// "It's a match" sheet: hero card, mode-specific CTAs, up to two alternate
/// picks, and the way back to the deck.
struct MatchView: View {
    let match: SwipeViewModel.Match
    let mode: SwipeMode
    let onConversion: (String, DeckCard) -> Void
    let onKeepSwiping: () -> Void

    var body: some View {
        ZStack {
            Theme.paper.ignoresSafeArea()
            ScrollView {
                VStack(spacing: Theme.space6) {
                    titleRow
                    SwipeCardView(card: match.primary)
                        .frame(height: MatchLayout.heroHeight)
                        .allowsHitTesting(false)
                    reasonLine
                    ctaSection
                    alternatesSection
                    SecondaryButton(title: "Keep swiping", action: onKeepSwiping)
                }
                .padding(Theme.space6)
            }
        }
    }

    // MARK: - Hero

    private var titleRow: some View {
        HStack(spacing: Theme.space3) {
            Image(systemName: "sparkles")
                .font(.title2)
                .foregroundStyle(Theme.accent)
                .accessibilityHidden(true)
            Text("It's a match")
                .font(.munchTitle)
                .foregroundStyle(Theme.ink)
        }
        .padding(.top, Theme.space5)
        .accessibilityAddTraits(.isHeader)
    }

    private var reasonLine: some View {
        Text(match.primary.reason)
            .font(.headline)
            .foregroundStyle(Theme.accent)
            .multilineTextAlignment(.center)
            .accessibilityLabel("Why this match: \(match.primary.reason)")
    }

    // MARK: - CTAs (log first, then open)

    @ViewBuilder
    private var ctaSection: some View {
        VStack(spacing: Theme.space4) {
            switch mode {
            case .dineIn:
                PrimaryButton(title: "Directions") {
                    logAndOpen(directionsURLString, conversionType: "directions")
                }
                if let phone = match.primary.phone {
                    SecondaryButton(title: "Call") {
                        logAndOpen(telURLString(for: phone), conversionType: "call")
                    }
                }
            case .pickup:
                PrimaryButton(title: "Find on DoorDash") {
                    logAndOpen(doorDashURLString, conversionType: "order_pickup")
                }
            case .delivery:
                PrimaryButton(title: "Find on DoorDash") {
                    logAndOpen(doorDashURLString, conversionType: "order_delivery")
                }
                SecondaryButton(title: "Find on Uber Eats") {
                    logAndOpen(uberEatsURLString, conversionType: "order_delivery")
                }
            }
        }
    }

    /// Log the conversion FIRST, then hand off. The log is fire-and-forget
    /// upstream, so it never delays the open.
    private func logAndOpen(_ urlString: String, conversionType: String) {
        onConversion(conversionType, match.primary)
        guard let url = URL(string: urlString) else { return }
        UIApplication.shared.open(url)
    }

    private var directionsURLString: String {
        "https://maps.apple.com/?daddr=\(match.primary.lat),\(match.primary.lon)"
    }

    private var doorDashURLString: String {
        "https://www.doordash.com/search/store/\(encodedPrimaryName)"
    }

    private var uberEatsURLString: String {
        "https://www.ubereats.com/search?q=\(encodedPrimaryName)"
    }

    private var encodedPrimaryName: String {
        let name = match.primary.name
        return name.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? name
    }

    /// tel: URLs reject spaces and punctuation — keep only digits and "+".
    private func telURLString(for phone: String) -> String {
        "tel:" + phone.filter { "+0123456789".contains($0) }
    }

    // MARK: - Alternates

    @ViewBuilder
    private var alternatesSection: some View {
        if !match.alternates.isEmpty {
            VStack(alignment: .leading, spacing: Theme.space4) {
                Text("Also great")
                    .font(.munchHeading)
                    .foregroundStyle(Theme.ink)
                    .accessibilityAddTraits(.isHeader)
                ForEach(match.alternates) { card in
                    alternateRow(card)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    /// Compact, non-interactive row (v1 keeps alternates informational).
    private func alternateRow(_ card: DeckCard) -> some View {
        let cuisine = CuisineCatalog.display(for: card.cuisines.first ?? "")
        return HStack(spacing: Theme.space4) {
            Text(cuisine.emoji)
                .font(.title3)
                .accessibilityHidden(true)
            VStack(alignment: .leading, spacing: Theme.space2) {
                Text(card.name)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(Theme.ink)
                Text("\(cuisine.name) • \(card.distanceLabel)")
                    .font(.footnote)
                    .foregroundStyle(Theme.inkSecondary)
            }
            Spacer(minLength: 0)
        }
        .padding(Theme.space4)
        .frame(maxWidth: .infinity)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: Theme.radiusControl))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.radiusControl)
                .stroke(Theme.stroke, lineWidth: 1)
        )
        .accessibilityElement(children: .combine)
    }
}

/// Match-sheet layout constants.
private enum MatchLayout {
    static let heroHeight: CGFloat = 320
}
