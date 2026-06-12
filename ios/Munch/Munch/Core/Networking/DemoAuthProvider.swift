// The $0-demo auth provider: a stable, locally generated device identity.
//
// The demo backend runs with MUNCH_AUTH=dev, where the bearer token IS the
// uid — so this provider mints a UUID once, keeps it in the Keychain, and the
// whole product loop (profile, decks, swipes, deletion) works with zero
// Firebase configuration (the spec §10.8 degraded-mode guarantee).
//
// FUTURE(Phase 6): FirebaseAuthProvider replaces this behind the same
// AuthProviding seam — Sign in with Apple -> Firebase ID token. Views and
// view models never change.

import Foundation

struct DemoAuthProvider: AuthProviding {
    private static let key = "munch.demo.uid"

    func currentToken() async throws -> String {
        if let existing = Keychain.get(Self.key) {
            return existing
        }
        let fresh = "demo-\(UUID().uuidString.lowercased())"
        Keychain.set(fresh, for: Self.key)
        return fresh
    }

    /// Called by account deletion: a deleted demo identity never comes back.
    static func reset() {
        Keychain.delete(key)
    }
}
