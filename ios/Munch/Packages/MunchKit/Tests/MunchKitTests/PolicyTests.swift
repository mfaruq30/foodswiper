// Match + pre-fetch policies: small rules, load-bearing behavior.

@testable import MunchKit
import XCTest

final class PolicyTests: XCTestCase {
    private func card(_ id: String, position: Int) -> DeckCard {
        DeckCard(
            restaurantId: id, name: id, cuisines: ["pizza"], priceTier: 2,
            priceImputed: true, distanceM: 400, lat: 40.73, lon: -73.99, phone: nil,
            reason: "r", position: position, explore: false
        )
    }

    func testNoMatchBeforeThreshold() {
        XCTAssertNil(MatchPolicy.match(rightSwipes: [card("a", position: 0)]))
        XCTAssertNil(MatchPolicy.match(rightSwipes: [card("a", position: 0), card("b", position: 1)]))
    }

    func testMatchPicksBestRankedRightSwipe() {
        // Swiped in order 5, 0, 2 — the match is the best-RANKED (position 0),
        // not the most recent, with the others as alternates.
        let result = MatchPolicy.match(
            rightSwipes: [card("c", position: 5), card("a", position: 0), card("b", position: 2)]
        )
        XCTAssertEqual(result?.primary.restaurantId, "a")
        XCTAssertEqual(result?.alternates.map(\.restaurantId), ["b", "c"])
    }

    func testAlternatesCapAtTwo() {
        let swipes = (0 ..< 5).map { card("r\($0)", position: $0) }
        let result = MatchPolicy.match(rightSwipes: swipes)
        XCTAssertEqual(result?.alternates.count, 2)
    }

    func testPrefetchTriggersAtThresholdOnlyWhenIdle() {
        XCTAssertTrue(DeckQueuePolicy.shouldPrefetch(remaining: 4, fetchInFlight: false))
        XCTAssertTrue(DeckQueuePolicy.shouldPrefetch(remaining: 0, fetchInFlight: false))
        XCTAssertFalse(DeckQueuePolicy.shouldPrefetch(remaining: 5, fetchInFlight: false))
        XCTAssertFalse(DeckQueuePolicy.shouldPrefetch(remaining: 2, fetchInFlight: true))
    }
}
