// The deck screen — Munch's home (spec §4.2). Thin by design: session logic
// lives in SwipeViewModel; this file is layout, state routing (loading /
// error / empty / deck), and the always-available button swipe path that
// keeps the gesture accessible (spec §14.4).

import MunchKit
import SwiftUI

/// Main swipe surface: wordmark, mode tabs, fallback-location banner, the
/// card stack, Pass/Like controls, and the match sheet.
struct SwipeScreen: View {
    @Environment(AppContainer.self) private var container
    @State private var viewModel = SwipeViewModel()
    @State private var didStartInitialLoad = false

    var body: some View {
        GeometryReader { proxy in
            VStack(spacing: Theme.space5) {
                header
                if viewModel.usingFallbackLocation {
                    fallbackBanner
                }
                deckContent(height: proxy.size.height * ScreenLayout.deckHeightRatio)
                Spacer(minLength: 0)
                if deckActive {
                    controls
                }
            }
            .padding(.horizontal, Theme.space5)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
        }
        .background(Theme.paper.ignoresSafeArea())
        .task {
            // `.task` re-runs on every appearance (tab switches); the deck
            // session must survive those, so load exactly once.
            guard !didStartInitialLoad else { return }
            didStartInitialLoad = true
            await viewModel.loadInitial(container: container)
        }
        .sheet(item: $viewModel.presentedMatch) { match in
            MatchView(
                match: match,
                mode: viewModel.mode,
                onConversion: { type, card in
                    viewModel.recordConversion(type, card: card, container: container)
                },
                onKeepSwiping: { viewModel.keepSwiping() }
            )
        }
    }

    // MARK: - Header

    private var header: some View {
        VStack(spacing: Theme.space4) {
            Text("Munch")
                .font(.display(ScreenLayout.wordmarkSize))
                .foregroundStyle(Theme.ink)
                .accessibilityAddTraits(.isHeader)
            modeTabs
        }
        .padding(.top, Theme.space4)
        .frame(maxWidth: .infinity)
    }

    private var modeTabs: some View {
        HStack(spacing: Theme.space3) {
            ForEach(SwipeMode.allCases, id: \.self) { tab in
                modeTab(tab)
            }
        }
    }

    private func modeTab(_ tab: SwipeMode) -> some View {
        let selected = tab == viewModel.mode
        return Button {
            Task { await viewModel.changeMode(tab, container: container) }
        } label: {
            Text(tab.displayName)
                .font(.subheadline.weight(.semibold))
                .padding(.horizontal, Theme.space5)
                .frame(minHeight: ScreenLayout.minTapTarget)
        }
        .background(selected ? Theme.accent : Theme.surface)
        .foregroundStyle(selected ? Color.white : Theme.ink)
        .clipShape(Capsule())
        .overlay(Capsule().stroke(selected ? Theme.accent : Theme.stroke, lineWidth: 1.5))
        .accessibilityLabel("\(tab.displayName) mode")
        .accessibilityAddTraits(selected ? [.isSelected] : [])
    }

    /// Honest-location banner (never a silent fake fix — LocationProvider's
    /// contract).
    private var fallbackBanner: some View {
        Text("Using \(viewModel.metroDisplayName) center — enable location for nearby picks")
            .font(.footnote)
            .foregroundStyle(Theme.inkSecondary)
            .multilineTextAlignment(.center)
            .frame(maxWidth: .infinity)
    }

    // MARK: - Deck states

    @ViewBuilder
    private func deckContent(height: CGFloat) -> some View {
        if viewModel.loading {
            ProgressView()
                .controlSize(.large)
                .tint(Theme.accent)
                .frame(maxWidth: .infinity, minHeight: height)
                .accessibilityLabel("Loading restaurants")
        } else if let message = viewModel.errorMessage {
            StateMessage(
                icon: "wifi.exclamationmark",
                title: "Connection trouble",
                detail: message,
                retryTitle: "Try again",
                retry: { Task { await viewModel.loadInitial(container: container) } }
            )
            .frame(maxWidth: .infinity, minHeight: height)
        } else if viewModel.cards.isEmpty {
            emptyState
                .frame(maxWidth: .infinity, minHeight: height)
        } else {
            SwipeCardStack(cards: viewModel.cards) { card, decision in
                // A fast button tap during a fly-off could desync the stack's
                // reported card from the queue front — drop the stale report.
                guard card.id == viewModel.cards.first?.id else { return }
                viewModel.swipe(decision, container: container)
            }
            .frame(height: height)
        }
    }

    @ViewBuilder
    private var emptyState: some View {
        if viewModel.emptyReason == "no_dietary_matches" {
            StateMessage(
                icon: "fork.knife",
                title: "Nothing matches your filters here",
                detail: "Try widening your search or relaxing dietary filters.",
                retryTitle: nil,
                retry: nil
            )
        } else {
            StateMessage(
                icon: "sparkles",
                title: "That's everyone nearby",
                detail: "Check back soon — or switch modes.",
                retryTitle: nil,
                retry: nil
            )
        }
    }

    // MARK: - Controls (the accessible swipe path)

    private var deckActive: Bool {
        !viewModel.loading && viewModel.errorMessage == nil && !viewModel.cards.isEmpty
    }

    private var controls: some View {
        HStack(spacing: Theme.space6) {
            deckControl(
                icon: "xmark", tint: Theme.nope, label: "Pass",
                identifier: "swipe-nope",
                hint: "Swipes left on the current restaurant"
            ) {
                viewModel.swipe(.left, container: container)
            }
            deckControl(
                icon: "heart.fill", tint: Theme.yes, label: "Like",
                identifier: "swipe-yes",
                hint: "Swipes right on the current restaurant"
            ) {
                viewModel.swipe(.right, container: container)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(.bottom, Theme.space5)
    }

    private func deckControl(
        icon: String, tint: Color, label: String, identifier: String, hint: String,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.title2.weight(.bold))
                .frame(
                    width: ScreenLayout.controlDiameter,
                    height: ScreenLayout.controlDiameter
                )
        }
        .background(Theme.surface)
        .foregroundStyle(tint)
        .clipShape(Circle())
        .overlay(Circle().stroke(Theme.stroke, lineWidth: 1.5))
        .accessibilityLabel(label)
        // Stable handle for the ios-e2e gate test (DemoFlowUITests).
        .accessibilityIdentifier(identifier)
        .accessibilityHint(hint)
    }
}

/// Screen layout constants (spec §4.2 proportions, named per design rule).
private enum ScreenLayout {
    static let wordmarkSize: CGFloat = 22
    static let deckHeightRatio: CGFloat = 0.62
    static let controlDiameter: CGFloat = 56
    static let minTapTarget: CGFloat = 44
}
