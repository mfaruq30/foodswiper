// Onboarding step: the cuisine grid (spec §4.2, 5+ required). Chips carry
// canonical cuisine IDs from CuisineCatalog — never display strings — so the
// picks line up with the server's adjacency map in ProfileBody.

import MunchKit
import SwiftUI

/// Cuisine multi-select grid; continue unlocks at
/// `CuisineCatalog.minimumSelection` picks.
struct CuisineSelectView: View {
    @Bindable var viewModel: OnboardingViewModel
    let onContinue: () -> Void

    private let columns = [
        GridItem(.flexible(), spacing: Theme.space4),
        GridItem(.flexible(), spacing: Theme.space4),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.space5) {
            header

            ScrollView(showsIndicators: false) {
                LazyVGrid(columns: columns, spacing: Theme.space4) {
                    ForEach(CuisineCatalog.onboarding) { cuisine in
                        SelectableChip(
                            label: cuisine.displayName,
                            emoji: cuisine.emoji,
                            selected: viewModel.selectedCuisines.contains(cuisine.id),
                            action: { toggle(cuisine.id) }
                        )
                    }
                }
                .padding(.vertical, Theme.space2)
            }

            counter

            PrimaryButton(title: "Continue", enabled: viewModel.canContinueCuisines, action: onContinue)
        }
        .padding(.horizontal, Theme.space5)
        .padding(.bottom, Theme.space5)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: Theme.space3) {
            Text("What do you crave?")
                .font(.munchHeading)
                .foregroundStyle(Theme.ink)
            Text("Pick at least \(CuisineCatalog.minimumSelection).")
                .font(.body)
                .foregroundStyle(Theme.inkSecondary)
        }
    }

    /// Live "N of 5 picked" tally; turns accent once the gate is met.
    private var counter: some View {
        Text("\(viewModel.selectedCuisines.count) of \(CuisineCatalog.minimumSelection) picked")
            .font(.subheadline.weight(.medium))
            .foregroundStyle(viewModel.canContinueCuisines ? Theme.accent : Theme.inkSecondary)
            .frame(maxWidth: .infinity)
            .accessibilityLabel(
                "\(viewModel.selectedCuisines.count) of \(CuisineCatalog.minimumSelection) cuisines picked"
            )
    }

    private func toggle(_ id: String) {
        if viewModel.selectedCuisines.contains(id) {
            viewModel.selectedCuisines.remove(id)
        } else {
            viewModel.selectedCuisines.insert(id)
        }
    }
}
