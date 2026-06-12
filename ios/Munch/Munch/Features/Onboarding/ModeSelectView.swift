// Onboarding final step: pick the default discovery mode, then submit the
// whole profile. The choice lands in AppContainer.preferredMode so the deck
// opens on the right tab; a successful save sets homeMetro and exits the flow.

import MunchKit
import SwiftUI

/// Mode picker plus the submit moment that completes onboarding.
struct ModeSelectView: View {
    @Environment(AppContainer.self) private var container
    @Bindable var viewModel: OnboardingViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.space5) {
            Text("How are you eating?")
                .font(.munchHeading)
                .foregroundStyle(Theme.ink)

            VStack(spacing: Theme.space4) {
                ForEach(SwipeMode.allCases, id: \.self) { mode in
                    ModeCard(
                        mode: mode,
                        selected: viewModel.mode == mode,
                        action: { viewModel.mode = mode }
                    )
                }
            }

            Spacer()

            if let message = viewModel.errorMessage {
                Text(message)
                    .font(.footnote)
                    .foregroundStyle(Theme.nope)
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
            }

            submitButton
        }
        .padding(.horizontal, Theme.space5)
        .padding(.bottom, Theme.space5)
    }

    /// "Start swiping" doubles as the retry button after a failed save.
    @ViewBuilder
    private var submitButton: some View {
        if viewModel.submitting {
            ProgressView()
                .tint(Theme.accent)
                .frame(maxWidth: .infinity, minHeight: 54)
                .accessibilityLabel("Saving your profile")
        } else {
            PrimaryButton(title: "Start swiping") {
                Task { await viewModel.submit(container: container) }
            }
        }
    }
}

// MARK: - Mode card

/// One large selectable row, styled like SelectableChip's selected state.
private struct ModeCard: View {
    let mode: SwipeMode
    let selected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: Theme.space4) {
                Text(emoji)
                    .font(.title)
                    .accessibilityHidden(true)
                VStack(alignment: .leading, spacing: Theme.space2) {
                    Text(mode.displayName)
                        .font(.headline)
                        .foregroundStyle(selected ? Theme.accent : Theme.ink)
                    Text(caption)
                        .font(.caption)
                        .foregroundStyle(Theme.inkSecondary)
                }
                Spacer()
                if selected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(Theme.accent)
                }
            }
            .padding(Theme.space5)
            .frame(maxWidth: .infinity, minHeight: 60, alignment: .leading)
        }
        .background(selected ? Theme.accentSoft : Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: Theme.radiusControl))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.radiusControl)
                .stroke(selected ? Theme.accent : Theme.stroke, lineWidth: 1.5)
        )
        .accessibilityLabel("\(mode.displayName). \(caption)")
        .accessibilityAddTraits(selected ? [.isSelected] : [])
    }

    private var emoji: String {
        switch mode {
        case .dineIn: "🍽️"
        case .pickup: "🥡"
        case .delivery: "🛵"
        }
    }

    private var caption: String {
        switch mode {
        case .dineIn: "Table for now"
        case .pickup: "Grab and go"
        case .delivery: "To your door"
        }
    }
}
