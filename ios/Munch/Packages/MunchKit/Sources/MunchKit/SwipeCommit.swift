// The gesture-commit math behind the swipe card stack — pure functions so the
// make-or-break UX moment (spec §4.3) is unit-tested in isolation from any
// view. The SwiftUI layer feeds in drag translation + predicted end position
// and renders whatever this returns; it makes no decisions of its own.

import Foundation

/// Outcome of evaluating a drag gesture against the commit thresholds.
public enum SwipeDecision: Equatable, Sendable {
    case none // snap back
    case left // nope
    case right // yes
}

/// Tunable physics constants. In one place (not scattered through views) so
/// feel-tuning during device testing touches exactly one file.
public enum SwipePhysics {
    /// Horizontal distance (pt) past which a release commits.
    public static let commitDistance: CGFloat = 110
    /// Predicted-end-translation distance that commits on a fast flick even
    /// when the finger hasn't traveled `commitDistance` yet.
    public static let flickPredictedDistance: CGFloat = 260
    /// Max card rotation (degrees) at full drag.
    public static let maxRotationDegrees: CGFloat = 12
    /// Drag distance at which rotation and indicator opacity saturate.
    public static let saturationDistance: CGFloat = 240
}

public enum SwipeCommit {
    /// Decide a release: distance beats the threshold, or the flick's
    /// predicted end does (velocity is captured by SwiftUI's prediction).
    public static func decision(
        translationX: CGFloat,
        predictedEndX: CGFloat,
        commitDistance: CGFloat = SwipePhysics.commitDistance,
        flickDistance: CGFloat = SwipePhysics.flickPredictedDistance
    ) -> SwipeDecision {
        if abs(translationX) >= commitDistance {
            return translationX > 0 ? .right : .left
        }
        // A flick must agree in direction with the actual travel — a wobble
        // that ends with opposite prediction must not commit.
        if abs(predictedEndX) >= flickDistance,
           predictedEndX.sign == translationX.sign, translationX != 0 {
            return predictedEndX > 0 ? .right : .left
        }
        return .none
    }

    /// Card rotation (degrees) proportional to horizontal offset, clamped.
    public static func rotationDegrees(translationX: CGFloat) -> CGFloat {
        let progress = max(-1, min(1, translationX / SwipePhysics.saturationDistance))
        return progress * SwipePhysics.maxRotationDegrees
    }

    /// Indicator strength in [0, 1]: positive drags feed YES, negative NOPE.
    /// Returned per side so the view never re-derives sign conventions.
    public static func indicatorOpacity(translationX: CGFloat) -> (nope: CGFloat, yes: CGFloat) {
        let progress = min(1, abs(translationX) / SwipePhysics.commitDistance)
        return translationX < 0 ? (progress, 0) : (0, progress)
    }
}
