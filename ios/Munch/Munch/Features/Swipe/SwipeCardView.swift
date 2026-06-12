// One card's face — pure presentation, zero gesture logic (the stack owns
// gestures, so this same view can sit non-interactive in the match sheet).
// The art region is the product's visual identity (CardArt — open data has no
// photos, D-010) and takes the top ~46% of the card; the reason chip — the
// product's signature moment — pins to the bottom.

import MunchKit
import SwiftUI

/// The face of a single deck card: art, name, meta row, reason chip.
/// Rendered full-size in `SwipeCardStack` and smaller in `MatchView`.
struct SwipeCardView: View {
    let card: DeckCard

    var body: some View {
        Theme.cardShadow(face)
    }

    // MARK: - Pieces

    private var face: some View {
        GeometryReader { proxy in
            VStack(alignment: .leading, spacing: 0) {
                art(height: proxy.size.height * CardLayout.artHeightRatio)
                details
            }
        }
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: Theme.radiusCard))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.radiusCard)
                .stroke(Theme.stroke, lineWidth: CardLayout.strokeWidth)
        )
    }

    /// Top region: cuisine-keyed art, clipped by the card's rounded shape so
    /// the top corners follow `Theme.radiusCard` without a second mask.
    private func art(height: CGFloat) -> some View {
        CardArt(venueId: card.restaurantId, cuisine: card.cuisines.first ?? "")
            .frame(maxWidth: .infinity)
            .frame(height: height)
            .clipped()
            .overlay(alignment: .topLeading) { exploreBadge }
    }

    @ViewBuilder
    private var exploreBadge: some View {
        if card.explore {
            Text("DISCOVER")
                .font(.caption2.weight(.bold))
                .padding(.horizontal, Theme.space4)
                .padding(.vertical, Theme.space2)
                .background(Theme.accentSoft)
                .foregroundStyle(Theme.accent)
                .clipShape(Capsule())
                .padding(Theme.space4)
                .accessibilityLabel("Discovery pick, outside your usual tastes")
        }
    }

    private var details: some View {
        VStack(alignment: .leading, spacing: Theme.space4) {
            Text(card.name)
                .font(.munchCardName)
                .foregroundStyle(Theme.ink)
                .lineLimit(2)
                .minimumScaleFactor(CardLayout.nameMinimumScale)
            metaRow
            Spacer(minLength: Theme.space3)
            ReasonChip(reason: card.reason)
        }
        .padding(Theme.space5)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private var metaRow: some View {
        let cuisine = CuisineCatalog.display(for: card.cuisines.first ?? "")
        return HStack(spacing: Theme.space3) {
            Text("\(cuisine.emoji) \(cuisine.name)")
                .font(.subheadline.weight(.medium))
            metaDot
            PriceLabel(tier: card.priceTier, imputed: card.priceImputed)
            metaDot
            HStack(spacing: Theme.space2) {
                Image(systemName: "location.fill")
                    .font(.caption2)
                    .accessibilityHidden(true)
                Text(card.distanceLabel)
                    .font(.subheadline.weight(.medium))
                    .accessibilityLabel("\(card.distanceLabel) away")
            }
        }
        .foregroundStyle(Theme.inkSecondary)
        .lineLimit(1)
    }

    private var metaDot: some View {
        Text("•")
            .font(.subheadline)
            .accessibilityHidden(true)
    }
}

/// Card-internal layout constants (spec §4.3's proportions, named so no
/// magic numbers leak into the view body).
private enum CardLayout {
    static let artHeightRatio: CGFloat = 0.46
    static let nameMinimumScale: CGFloat = 0.7
    static let strokeWidth: CGFloat = 1
}
