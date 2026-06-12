// The swipe gesture engine — the make-or-break interaction (spec §4.3).
//
// Renders the top three cards; ONLY the front card takes the drag. Every
// commit decision (distance, flick, rotation, stamp opacity) comes from
// MunchKit's SwipeCommit so the physics stay unit-tested; this view renders
// what the math says and animates the exit. Swiping is ALSO reachable without
// the gesture: the screen's Pass/Like buttons drive the same onSwipe path.

import Foundation
import MunchKit
import SwiftUI

/// Interactive deck: drag the front card, watch the YES/NOPE stamps, release
/// to commit. Reports every committed swipe through `onSwipe` AFTER the
/// fly-off animation, so the queue pop never makes the card jump.
struct SwipeCardStack: View {
    let cards: [DeckCard]
    let onSwipe: (DeckCard, SwipeDecision) -> Void

    @State private var dragTranslation: CGSize = .zero
    @State private var isFlyingOff = false

    private var visibleCards: [DeckCard] {
        Array(cards.prefix(StackLayout.visibleDepth))
    }

    var body: some View {
        ZStack {
            ForEach(visibleCards) { card in
                let index = visibleCards.firstIndex(of: card) ?? 0
                deckCard(card, at: index)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .animation(.spring(), value: visibleCards.map(\.id))
        .onChange(of: cards.first?.id) {
            // The front card can also change underneath us (button swipes,
            // prefetch replace) — never let a stale drag offset carry over.
            dragTranslation = .zero
        }
        .accessibilityElement(children: .contain)
    }

    // MARK: - One card in the stack

    @ViewBuilder
    private func deckCard(_ card: DeckCard, at index: Int) -> some View {
        let isTop = index == 0
        SwipeCardView(card: card)
            .overlay(alignment: .topLeading) {
                if isTop { yesStamp }
            }
            .overlay(alignment: .topTrailing) {
                if isTop { nopeStamp }
            }
            .scaleEffect(restingScale(at: index))
            .offset(y: restingYOffset(at: index))
            .offset(isTop ? dragTranslation : .zero)
            .rotationEffect(.degrees(isTop ? topRotationDegrees : 0))
            .zIndex(Double(StackLayout.visibleDepth - index))
            .gesture(dragGesture, including: isTop && !isFlyingOff ? .all : .subviews)
            .accessibilityElement(children: .combine)
            .accessibilityLabel(accessibilityText(for: card))
            .accessibilityHint("Use the Pass and Like buttons below to decide.")
            .accessibilityHidden(!isTop)
    }

    // MARK: - Gesture

    private var dragGesture: some Gesture {
        DragGesture()
            .onChanged { value in
                dragTranslation = value.translation
            }
            .onEnded { value in
                let decision = SwipeCommit.decision(
                    translationX: value.translation.width,
                    predictedEndX: value.predictedEndTranslation.width
                )
                switch decision {
                case .none:
                    withAnimation(.spring()) { dragTranslation = .zero }
                case .left, .right:
                    flyOff(decision)
                }
            }
    }

    /// Animate the front card off-screen, then report the swipe. The state
    /// reset and the callback land in the same run-loop tick, so the next
    /// card promotes without a flash of the old offset.
    private func flyOff(_ decision: SwipeDecision) {
        guard let card = cards.first else { return }
        isFlyingOff = true
        let exitX = decision == .right ? StackLayout.exitDistance : -StackLayout.exitDistance
        withAnimation(.easeOut(duration: StackLayout.exitDuration)) {
            dragTranslation = CGSize(width: exitX, height: dragTranslation.height)
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + StackLayout.exitDuration) {
            dragTranslation = .zero
            isFlyingOff = false
            onSwipe(card, decision)
        }
    }

    // MARK: - Stamps and geometry

    private var topRotationDegrees: Double {
        Double(SwipeCommit.rotationDegrees(translationX: dragTranslation.width))
    }

    private var yesStamp: some View {
        stamp(
            "YES", color: Theme.yes, rotation: -StackLayout.stampRotationDegrees,
            opacity: SwipeCommit.indicatorOpacity(translationX: dragTranslation.width).yes
        )
    }

    private var nopeStamp: some View {
        stamp(
            "NOPE", color: Theme.nope, rotation: StackLayout.stampRotationDegrees,
            opacity: SwipeCommit.indicatorOpacity(translationX: dragTranslation.width).nope
        )
    }

    private func stamp(
        _ word: String, color: Color, rotation: Double, opacity: CGFloat
    ) -> some View {
        Text(word)
            .font(.system(size: StackLayout.stampFontSize, weight: .heavy))
            .foregroundStyle(color)
            .padding(.horizontal, Theme.space4)
            .padding(.vertical, Theme.space2)
            .overlay(
                RoundedRectangle(cornerRadius: Theme.radiusControl)
                    .stroke(color, lineWidth: StackLayout.stampStrokeWidth)
            )
            .rotationEffect(.degrees(rotation))
            .opacity(opacity)
            .padding(Theme.space6)
            .accessibilityHidden(true)
    }

    private func restingScale(at index: Int) -> CGFloat {
        1 - CGFloat(index) * StackLayout.backScaleStep
    }

    private func restingYOffset(at index: Int) -> CGFloat {
        CGFloat(index) * StackLayout.backYOffsetStep
    }

    private func accessibilityText(for card: DeckCard) -> String {
        let cuisine = CuisineCatalog.display(for: card.cuisines.first ?? "").name
        return "\(card.name), \(cuisine), \(card.distanceLabel). \(card.reason)"
    }
}

/// Stack physics and layout constants (the spec's numbers, named).
private enum StackLayout {
    static let visibleDepth = 3
    static let backScaleStep: CGFloat = 0.05
    static let backYOffsetStep: CGFloat = 10
    static let exitDistance: CGFloat = 600
    static let exitDuration: TimeInterval = 0.25
    static let stampRotationDegrees: Double = 12
    static let stampFontSize: CGFloat = 32
    static let stampStrokeWidth: CGFloat = 3
}
