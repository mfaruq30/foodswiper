// Locks Metro's wire contract — the raw values live in Postgres
// (`profiles.home_metro`), so a rename here would corrupt the API silently.

@testable import MunchKit
import XCTest

final class MetroTests: XCTestCase {
    func testRawValuesMatchDatabaseEnum() {
        XCTAssertEqual(Metro.nyc.rawValue, "nyc")
        XCTAssertEqual(Metro.boston.rawValue, "boston")
    }

    func testDisplayNamesAreHumanReadable() {
        XCTAssertEqual(Metro.nyc.displayName, "New York City")
        XCTAssertEqual(Metro.boston.displayName, "Boston")
    }

    func testV1ShipsExactlyTwoMetros() {
        // Spec §1: NYC + Boston only. A third case must be a deliberate,
        // reviewed decision — this test forces that conversation.
        XCTAssertEqual(Metro.allCases.count, 2)
    }
}
