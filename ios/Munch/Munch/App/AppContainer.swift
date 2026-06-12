// Composition root: builds the adapter set the whole app shares
// (spec §2: protocol-based DI, no framework).
//
// Demo configuration is environment-first so the SAME build serves the
// simulator demo and CI UI tests: MUNCH_API_URL overrides the backend
// (default localhost:8123 — the uvicorn memory-mode demo on the host machine).

import Foundation
import Observation
import SwiftUI

@Observable
@MainActor
final class AppContainer {
    let api: APIClient
    let location = LocationProvider()

    /// Persisted onboarding state: nil until onboarding completes, then the
    /// chosen metro. Kept in UserDefaults (it is preference, not secret).
    var homeMetro: String? {
        didSet { UserDefaults.standard.set(homeMetro, forKey: "munch.homeMetro") }
    }

    /// The user's preferred mode from onboarding (default deck tab).
    var preferredMode: String {
        didSet { UserDefaults.standard.set(preferredMode, forKey: "munch.preferredMode") }
    }

    init() {
        let env = ProcessInfo.processInfo.environment
        // UI tests need a virgin install every run: wipe onboarding state and
        // the demo identity before anything reads them. Guarded by an explicit
        // env flag the test runner sets; unreachable in normal launches.
        if env["MUNCH_UITEST_RESET"] == "1" {
            UserDefaults.standard.removeObject(forKey: "munch.homeMetro")
            UserDefaults.standard.removeObject(forKey: "munch.preferredMode")
            DemoAuthProvider.reset()
        }
        let urlString = env["MUNCH_API_URL"] ?? "http://localhost:8123"
        // A malformed override falls back to the demo default rather than
        // crashing at launch — the URL is operator input, not user input.
        let base = URL(string: urlString) ?? URL(string: "http://localhost:8123")!
        api = APIClient(baseURL: base, auth: DemoAuthProvider())
        homeMetro = UserDefaults.standard.string(forKey: "munch.homeMetro")
        preferredMode = UserDefaults.standard.string(forKey: "munch.preferredMode") ?? "dine_in"
    }

    /// Account deletion (D-013): server purge first, then local identity.
    func deleteAccountAndReset() async throws {
        try await api.deleteAccount()
        DemoAuthProvider.reset()
        homeMetro = nil
        UserDefaults.standard.removeObject(forKey: "munch.homeMetro")
    }
}
