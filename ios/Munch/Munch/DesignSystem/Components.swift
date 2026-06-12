// Reusable design-system components (spec §14.4's kit, in code form).
// Every interactive element: >= 44pt targets, VoiceOver labels, Dynamic Type.

import SwiftUI

/// Primary CTA — the warm-orange brand button.
struct PrimaryButton: View {
    let title: String
    var enabled: Bool = true
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.headline)
                .frame(maxWidth: .infinity, minHeight: 54)
        }
        .background(enabled ? Theme.accent : Theme.stroke)
        .foregroundStyle(enabled ? Color.white : Theme.inkSecondary)
        .clipShape(RoundedRectangle(cornerRadius: Theme.radiusControl))
        .disabled(!enabled)
        .accessibilityLabel(title)
        // Stable handle for XCUITests — identifiers must never localize.
        .accessibilityIdentifier(title)
    }
}

/// Secondary (outline) button.
struct SecondaryButton: View {
    let title: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.headline)
                .frame(maxWidth: .infinity, minHeight: 54)
        }
        .foregroundStyle(Theme.ink)
        .overlay(
            RoundedRectangle(cornerRadius: Theme.radiusControl).stroke(Theme.stroke, lineWidth: 1.5)
        )
        .accessibilityLabel(title)
    }
}

/// Selectable chip (cuisines, dietary flags).
struct SelectableChip: View {
    let label: String
    let emoji: String?
    let selected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: Theme.space2) {
                if let emoji {
                    Text(emoji)
                }
                Text(label)
                    .font(.subheadline.weight(.medium))
            }
            .padding(.horizontal, Theme.space5)
            .frame(minHeight: 44)
        }
        .background(selected ? Theme.accentSoft : Theme.surface)
        .foregroundStyle(selected ? Theme.accent : Theme.ink)
        .clipShape(Capsule())
        .overlay(
            Capsule().stroke(selected ? Theme.accent : Theme.stroke, lineWidth: 1.5)
        )
        .accessibilityLabel(label)
        .accessibilityIdentifier("chip-\(label)")
        .accessibilityAddTraits(selected ? [.isSelected] : [])
    }
}

/// Onboarding progress dots.
struct ProgressDots: View {
    let total: Int
    let current: Int

    var body: some View {
        HStack(spacing: Theme.space3) {
            ForEach(0 ..< total, id: \.self) { index in
                Capsule()
                    .fill(index <= current ? Theme.accent : Theme.stroke)
                    .frame(width: index == current ? 22 : 8, height: 8)
            }
        }
        .accessibilityLabel("Step \(current + 1) of \(total)")
    }
}

/// The per-card reason line — the product's signature moment, styled once.
struct ReasonChip: View {
    let reason: String

    var body: some View {
        HStack(spacing: Theme.space3) {
            Image(systemName: "sparkles")
                .font(.caption)
            Text(reason)
                .font(.footnote.weight(.medium))
                .lineLimit(2)
        }
        .padding(.horizontal, Theme.space4)
        .padding(.vertical, Theme.space3)
        .background(Theme.accentSoft)
        .foregroundStyle(Theme.accent)
        .clipShape(RoundedRectangle(cornerRadius: Theme.radiusControl))
        .accessibilityLabel("Why this match: \(reason)")
    }
}

/// Price tier as $ glyphs, with the imputed flag honestly surfaced (D-010).
struct PriceLabel: View {
    let tier: Int
    let imputed: Bool

    var body: some View {
        Text(String(repeating: "$", count: max(1, min(tier, 4))) + (imputed ? "?" : ""))
            .font(.subheadline.weight(.semibold))
            .foregroundStyle(Theme.inkSecondary)
            .accessibilityLabel(
                imputed ? "Price level \(tier), estimated" : "Price level \(tier)"
            )
    }
}

/// Centered empty/error state with an optional retry.
struct StateMessage: View {
    let icon: String
    let title: String
    let detail: String
    var retryTitle: String?
    var retry: (() -> Void)?

    var body: some View {
        VStack(spacing: Theme.space5) {
            Image(systemName: icon)
                .font(.system(size: 44))
                .foregroundStyle(Theme.inkSecondary)
            Text(title)
                .font(.munchHeading)
                .foregroundStyle(Theme.ink)
            Text(detail)
                .font(.body)
                .foregroundStyle(Theme.inkSecondary)
                .multilineTextAlignment(.center)
            if let retryTitle, let retry {
                PrimaryButton(title: retryTitle, action: retry)
                    .padding(.horizontal, Theme.space7)
            }
        }
        .padding(Theme.space6)
    }
}
