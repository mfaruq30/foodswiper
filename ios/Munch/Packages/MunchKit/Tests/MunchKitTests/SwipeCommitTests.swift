// The gesture-commit thresholds are the swipe feel — pin them (spec §4.3).

import XCTest

@testable import MunchKit

final class SwipeCommitTests: XCTestCase {
    func testUnderThresholdSnapsBack() {
        XCTAssertEqual(SwipeCommit.decision(translationX: 60, predictedEndX: 80), .none)
        XCTAssertEqual(SwipeCommit.decision(translationX: -90, predictedEndX: -100), .none)
    }

    func testDistanceCommit() {
        XCTAssertEqual(SwipeCommit.decision(translationX: 120, predictedEndX: 130), .right)
        XCTAssertEqual(SwipeCommit.decision(translationX: -111, predictedEndX: -90), .left)
    }

    func testFastFlickCommitsEarly() {
        // Finger only moved 50pt but the flick's predicted end clears the bar.
        XCTAssertEqual(SwipeCommit.decision(translationX: 50, predictedEndX: 300), .right)
        XCTAssertEqual(SwipeCommit.decision(translationX: -40, predictedEndX: -280), .left)
    }

    func testWobbleWithOppositePredictionDoesNotCommit() {
        // Dragged right, but prediction says left: directions disagree -> snap back.
        XCTAssertEqual(SwipeCommit.decision(translationX: 30, predictedEndX: -300), .none)
    }

    func testRotationIsProportionalAndClamped() {
        XCTAssertEqual(SwipeCommit.rotationDegrees(translationX: 0), 0)
        XCTAssertEqual(
            SwipeCommit.rotationDegrees(translationX: 240), SwipePhysics.maxRotationDegrees
        )
        XCTAssertEqual(
            SwipeCommit.rotationDegrees(translationX: -10_000),
            -SwipePhysics.maxRotationDegrees
        )
        XCTAssertLessThan(SwipeCommit.rotationDegrees(translationX: 120), 12)
    }

    func testIndicatorSidesNeverBleed() {
        let right = SwipeCommit.indicatorOpacity(translationX: 80)
        XCTAssertEqual(right.nope, 0)
        XCTAssertGreaterThan(right.yes, 0)
        let left = SwipeCommit.indicatorOpacity(translationX: -200)
        XCTAssertEqual(left.yes, 0)
        XCTAssertEqual(left.nope, 1) // saturates at the commit distance
    }
}
