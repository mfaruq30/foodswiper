// The Phase 4 gate test (spec §11): the FULL product loop — onboarding →
// deck → three right-swipes → match — against the live demo backend on the
// simulator. CI starts the memory-mode API (committed fixtures) and runs this;
// a green run IS the "full flow works against the live backend" evidence.

import XCTest

final class DemoFlowUITests: XCTestCase {
    func testOnboardThroughSwipeToMatch() throws {
        let app = XCUIApplication()
        // The runner passes the backend URL via TEST_RUNNER_MUNCH_API_URL;
        // forward it into the app so one env var configures the whole stack.
        if let api = ProcessInfo.processInfo.environment["MUNCH_API_URL"] {
            app.launchEnvironment["MUNCH_API_URL"] = api
        }
        // A fresh identity every run: deletion/“already onboarded” state from
        // a previous run must not leak in. The app honors this reset flag.
        app.launchEnvironment["MUNCH_UITEST_RESET"] = "1"
        app.launch()

        // Welcome → cuisines
        app.buttons["Get started"].tap()

        // Pick 5 cuisines (the minimum), then continue.
        for cuisine in ["Pizza", "Italian", "Ramen", "Korean", "Burgers"] {
            let chip = app.buttons["chip-\(cuisine)"]
            XCTAssertTrue(chip.waitForExistence(timeout: 5), "missing chip \(cuisine)")
            chip.tap()
        }
        app.buttons["Continue"].tap()

        // Anchors are optional — continue straight through.
        XCTAssertTrue(app.buttons["Continue"].waitForExistence(timeout: 5))
        app.buttons["Continue"].tap()

        // Mode select → start swiping (NYC default, demo backend).
        let start = app.buttons["Start swiping"]
        XCTAssertTrue(start.waitForExistence(timeout: 5))
        start.tap()

        // The deck must serve a real card from the fixture venues.
        let yes = app.buttons["swipe-yes"]
        XCTAssertTrue(yes.waitForExistence(timeout: 15), "deck never loaded — is the API up?")

        // Three right-swipes triggers the match (MatchPolicy.rightSwipesToMatch).
        for _ in 0 ..< 3 {
            yes.tap()
            // Brief settle between programmatic swipes.
            usleep(400_000)
        }
        XCTAssertTrue(
            app.staticTexts["It's a match"].waitForExistence(timeout: 10),
            "match screen did not appear after three right-swipes"
        )
    }
}
