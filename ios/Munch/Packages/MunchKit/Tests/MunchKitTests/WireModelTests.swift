// Decode fixtures pinned to the EXACT JSON the Munch API emits — a renamed
// server field fails here, not as a blank screen in the app.

import Foundation
@testable import MunchKit
import XCTest

final class WireModelTests: XCTestCase {
    func testDeckResponseDecodes() throws {
        let json = """
        {
          "request_id": "c566cab8-0000-0000-0000-000000000000",
          "model_version": "heuristic-v1",
          "empty_reason": null,
          "cards": [
            {
              "restaurant_id": "osm:node:4196029141",
              "name": "Lucali",
              "cuisines": ["pizza"],
              "price_tier": 2,
              "price_imputed": true,
              "distance_m": 537.4,
              "lat": 40.7305,
              "lon": -73.9989,
              "phone": "+1 718 858 4086",
              "reason": "You love Pizza — this one's 0.3 mi away",
              "position": 0,
              "explore": false
            }
          ]
        }
        """
        let deck = try JSONDecoder().decode(Deck.self, from: Data(json.utf8))
        XCTAssertEqual(deck.modelVersion, "heuristic-v1")
        XCTAssertNil(deck.emptyReason)
        XCTAssertEqual(deck.cards.first?.name, "Lucali")
        XCTAssertEqual(deck.cards.first?.distanceM ?? 0, 537.4, accuracy: 0.001)
        XCTAssertEqual(deck.cards.first?.lat ?? 0, 40.7305, accuracy: 0.0001)
        XCTAssertEqual(deck.cards.first?.phone, "+1 718 858 4086")
        XCTAssertEqual(deck.cards.first?.distanceLabel, "0.3 mi")
        XCTAssertFalse(deck.cards.first?.explore ?? true)
    }

    func testEmptyDeckCarriesTypedReason() throws {
        let json = """
        {"request_id": "x", "model_version": "heuristic-v1",
         "empty_reason": "no_dietary_matches", "cards": []}
        """
        let deck = try JSONDecoder().decode(Deck.self, from: Data(json.utf8))
        XCTAssertEqual(deck.emptyReason, "no_dietary_matches")
    }

    func testSwipeRequestEncodesSnakeCase() throws {
        let request = SwipeRequest(
            restaurantId: "osm:node:1", mode: .dineIn, direction: "right",
            sessionId: UUID(), requestId: UUID(), cardPosition: 3, explore: true
        )
        let data = try JSONEncoder().encode(request)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        // The server REQUIRES these exact keys (D-008 training-label fields).
        XCTAssertEqual(object["mode"] as? String, "dine_in")
        XCTAssertNotNil(object["request_id"])
        XCTAssertEqual(object["card_position"] as? Int, 3)
        XCTAssertEqual(object["explore"] as? Bool, true)
    }

    func testCuisineCatalogContract() {
        XCTAssertGreaterThanOrEqual(CuisineCatalog.onboarding.count, 15)
        XCTAssertEqual(CuisineCatalog.minimumSelection, 5)
        // Unknown nodes degrade gracefully instead of crashing card art.
        XCTAssertEqual(CuisineCatalog.display(for: "weird_future_cuisine").emoji, "🍽️")
        XCTAssertEqual(CuisineCatalog.display(for: "bbq").name, "BBQ")
    }
}
