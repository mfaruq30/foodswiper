// Onboarding step: metro + anchor restaurants. Anchors are the highest-signal
// taste input we collect (the "secret sauce"), but they stay optional — a
// small search index or a server miss must never block onboarding.

import MunchKit
import SwiftUI

/// Metro picker plus optional anchor-restaurant search and selection.
struct AnchorSearchView: View {
    @Environment(AppContainer.self) private var container
    @Bindable var viewModel: OnboardingViewModel
    let onContinue: () -> Void

    /// Keeps the result list scannable; the index rarely has more good hits.
    private let maxVisibleResults = 8

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.space5) {
            header
            metroPicker
            searchField
            resultsArea
            pickedRow
            footer
        }
        .padding(.horizontal, Theme.space5)
        .padding(.bottom, Theme.space5)
        .task(id: searchKey) {
            await viewModel.runSearch(container: container)
        }
    }

    /// Metro is part of the key so switching cities re-runs the same query
    /// against the newly selected metro.
    private var searchKey: String {
        viewModel.metro.rawValue + "|" + viewModel.searchQuery
    }

    // MARK: - Sections

    private var header: some View {
        VStack(alignment: .leading, spacing: Theme.space3) {
            Text("Name a few favorites")
                .font(.munchHeading)
                .foregroundStyle(Theme.ink)
            Text("Restaurants you already love teach Munch your taste. This is the secret sauce.")
                .font(.body)
                .foregroundStyle(Theme.inkSecondary)
        }
    }

    private var metroPicker: some View {
        Picker("Home metro", selection: $viewModel.metro) {
            ForEach(Metro.allCases, id: \.self) { metro in
                Text(metro.displayName).tag(metro)
            }
        }
        .pickerStyle(.segmented)
        .accessibilityLabel("Home metro")
    }

    private var searchField: some View {
        HStack(spacing: Theme.space3) {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(Theme.inkSecondary)
            TextField("Search restaurants", text: $viewModel.searchQuery)
                .font(.body)
                .foregroundStyle(Theme.ink)
                .autocorrectionDisabled()
                .textInputAutocapitalization(.words)
                .submitLabel(.search)
                .accessibilityLabel("Search restaurants")
        }
        .padding(.horizontal, Theme.space4)
        .frame(minHeight: 44)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: Theme.radiusControl))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.radiusControl)
                .stroke(Theme.stroke, lineWidth: 1.5)
        )
    }

    private var resultsArea: some View {
        ScrollView(showsIndicators: false) {
            LazyVStack(spacing: Theme.space3) {
                if viewModel.searching {
                    ProgressView()
                        .tint(Theme.accent)
                        .frame(maxWidth: .infinity)
                        .padding(.top, Theme.space3)
                } else if showNoResults {
                    Text("No matches — try another spelling.")
                        .font(.footnote)
                        .foregroundStyle(Theme.inkSecondary)
                        .frame(maxWidth: .infinity)
                        .padding(.top, Theme.space3)
                } else {
                    ForEach(visibleResults) { result in
                        AnchorResultRow(
                            result: result,
                            picked: viewModel.isAnchored(result),
                            action: { viewModel.toggleAnchor(result) }
                        )
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    @ViewBuilder
    private var pickedRow: some View {
        if !viewModel.anchors.isEmpty {
            VStack(alignment: .leading, spacing: Theme.space3) {
                Text(pickedCaption)
                    .font(.caption.weight(.medium))
                    .foregroundStyle(Theme.inkSecondary)
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: Theme.space3) {
                        ForEach(viewModel.anchors) { anchor in
                            SelectableChip(
                                label: anchor.name,
                                emoji: nil,
                                selected: true,
                                action: { viewModel.toggleAnchor(anchor) }
                            )
                            .accessibilityHint("Removes this favorite")
                        }
                    }
                }
            }
        }
    }

    private var footer: some View {
        VStack(spacing: Theme.space3) {
            Text("Optional — but even one helps a lot.")
                .font(.caption)
                .foregroundStyle(Theme.inkSecondary)
                .frame(maxWidth: .infinity)
            PrimaryButton(title: "Continue", action: onContinue)
        }
    }

    // MARK: - Derived state

    private var visibleResults: [SearchResult] {
        Array(viewModel.searchResults.prefix(maxVisibleResults))
    }

    private var showNoResults: Bool {
        let trimmed = viewModel.searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        return trimmed.count >= OnboardingViewModel.minimumQueryLength
            && viewModel.searchResults.isEmpty
    }

    private var pickedCaption: String {
        if viewModel.anchors.count == OnboardingViewModel.anchorLimit {
            return "Picked — that's the max of \(OnboardingViewModel.anchorLimit). Tap to remove."
        }
        return "Picked — tap to remove"
    }
}

// MARK: - Result row

/// One tappable search hit: name, cuisine line, pick indicator.
private struct AnchorResultRow: View {
    let result: SearchResult
    let picked: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: Theme.space4) {
                VStack(alignment: .leading, spacing: Theme.space2) {
                    Text(result.name)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(Theme.ink)
                        .lineLimit(1)
                    Text(cuisineLine)
                        .font(.caption)
                        .foregroundStyle(Theme.inkSecondary)
                        .lineLimit(1)
                }
                Spacer()
                Image(systemName: picked ? "checkmark.circle.fill" : "plus.circle")
                    .foregroundStyle(picked ? Theme.accent : Theme.inkSecondary)
            }
            .padding(.horizontal, Theme.space4)
            .padding(.vertical, Theme.space3)
            .frame(minHeight: 44)
        }
        .background(picked ? Theme.accentSoft : Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: Theme.radiusControl))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.radiusControl)
                .stroke(picked ? Theme.accent : Theme.stroke, lineWidth: 1.5)
        )
        .accessibilityLabel("\(result.name), \(cuisineLine)")
        .accessibilityAddTraits(picked ? [.isSelected] : [])
    }

    private var cuisineLine: String {
        result.cuisines.map { CuisineCatalog.display(for: $0).name }.joined(separator: " · ")
    }
}
