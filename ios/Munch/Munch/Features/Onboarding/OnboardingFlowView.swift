// Onboarding shell (spec §4.2): welcome → cuisines → metro+anchors → mode.
// A hand-rolled step switcher (not NavigationStack) because the flow is
// linear, short, and shares one view model; transitions stay dead simple.

import SwiftUI

/// Hosts the four onboarding steps and the shared `OnboardingViewModel`.
/// Completion is signalled by the view model setting `container.homeMetro`,
/// which the root coordinator observes to leave onboarding.
struct OnboardingFlowView: View {
    /// The linear step order; raw values give cheap back navigation.
    private enum Step: Int, CaseIterable {
        case welcome
        case cuisines
        case metroAnchors
        case mode
    }

    @State private var viewModel = OnboardingViewModel()
    @State private var step: Step = .welcome

    var body: some View {
        ZStack {
            Theme.paper.ignoresSafeArea()
            VStack(spacing: 0) {
                topBar
                ZStack {
                    stepContent
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
    }

    // MARK: - Chrome

    /// Back chevron + progress dots for the three post-welcome steps.
    private var topBar: some View {
        ZStack {
            if step != .welcome {
                HStack {
                    Button(action: goBack) {
                        Image(systemName: "chevron.left")
                            .font(.headline)
                            .foregroundStyle(Theme.ink)
                            .frame(width: 44, height: 44)
                            .contentShape(Rectangle())
                    }
                    .accessibilityLabel("Back")
                    Spacer()
                }
                ProgressDots(total: Step.allCases.count - 1, current: step.rawValue - 1)
            }
        }
        .frame(minHeight: 44)
        .padding(.horizontal, Theme.space5)
        .padding(.top, Theme.space3)
    }

    // MARK: - Steps

    @ViewBuilder
    private var stepContent: some View {
        switch step {
        case .welcome:
            WelcomeStep(onGetStarted: { advance(to: .cuisines) })
                .transition(stepTransition)
        case .cuisines:
            CuisineSelectView(viewModel: viewModel, onContinue: { advance(to: .metroAnchors) })
                .transition(stepTransition)
        case .metroAnchors:
            AnchorSearchView(viewModel: viewModel, onContinue: { advance(to: .mode) })
                .transition(stepTransition)
        case .mode:
            ModeSelectView(viewModel: viewModel)
                .transition(stepTransition)
        }
    }

    private var stepTransition: AnyTransition {
        .asymmetric(
            insertion: .move(edge: .trailing).combined(with: .opacity),
            removal: .move(edge: .leading).combined(with: .opacity)
        )
    }

    private func advance(to next: Step) {
        withAnimation(.easeInOut) { step = next }
    }

    private func goBack() {
        guard let previous = Step(rawValue: step.rawValue - 1) else { return }
        withAnimation(.easeInOut) { step = previous }
    }
}

// MARK: - Welcome

/// The brand moment: serif wordmark, tagline, one warm CTA.
private struct WelcomeStep: View {
    let onGetStarted: () -> Void

    var body: some View {
        VStack(spacing: Theme.space4) {
            Spacer()
            HStack(spacing: Theme.space5) {
                Text("🍜")
                Text("🌮")
                Text("🍕")
            }
            .font(.munchTitle)
            .accessibilityHidden(true)
            Text("Munch")
                .font(.munchTitle)
                .foregroundStyle(Theme.accent)
            Text("Stop deciding. Start eating.")
                .font(.body)
                .foregroundStyle(Theme.inkSecondary)
            Spacer()
            PrimaryButton(title: "Get started", action: onGetStarted)
            Text("About 90 seconds to set up")
                .font(.caption)
                .foregroundStyle(Theme.inkSecondary)
        }
        .padding(.horizontal, Theme.space6)
        .padding(.bottom, Theme.space5)
    }
}
