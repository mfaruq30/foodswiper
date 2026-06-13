// Composition root: builds the adapter set the whole app shares
// (spec §2: protocol-based DI, no framework).
//
// Auth selection is the one place the backend choice reaches the client. When
// Firebase is configured (a release build with GoogleService-Info.plist), the
// app uses Sign in with Apple via FirebaseAuthProvider; otherwise — the $0
// demo and CI — it uses DemoAuthProvider and the sign-in screen is skipped.
// MUNCH_API_URL overrides the backend (default localhost:8123, the uvicorn
// memory-mode demo on the host machine).

import Foundation
import Observation
import SwiftUI

@Observable
@MainActor
final class AppContainer {
    let api: APIClient
    let location = LocationProvider()

    /// Whether the user can enter the app. Demo mode is always signed in;
    /// Firebase mode reflects the persisted Apple/Firebase session (returning
    /// users are auto-signed-in, so the sign-in screen appears only once).
    private(set) var isSignedIn: Bool

    /// Persisted onboarding state: nil until onboarding completes, then the
    /// chosen metro. Kept in UserDefaults (it is preference, not secret).
    var homeMetro: String? {
        didSet { UserDefaults.standard.set(homeMetro, forKey: "munch.homeMetro") }
    }

    /// The user's preferred mode from onboarding (default deck tab).
    var preferredMode: String {
        didSet { UserDefaults.standard.set(preferredMode, forKey: "munch.preferredMode") }
    }

    /// The Firebase-backed auth provider, present only when Firebase is
    /// configured. nil => demo mode (no Sign in with Apple).
    private let firebaseAuth: FirebaseAuthProvider?

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

        // Configure Firebase iff the SDK is linked and a config plist is
        // bundled; absent in demo/CI. An explicit MUNCH_AUTH=dev forces demo
        // even when Firebase is present (useful for local testing).
        let firebaseActive = FirebaseBootstrap.configureIfAvailable()
        let forceDemo = env["MUNCH_AUTH"] == "dev" || env["MUNCH_UITEST_RESET"] == "1"

        let authProvider: AuthProviding
        if firebaseActive, !forceDemo {
            let provider = FirebaseAuthProvider()
            firebaseAuth = provider
            authProvider = provider
            isSignedIn = provider.isSignedIn // auto sign-in for returning users
        } else {
            firebaseAuth = nil
            authProvider = DemoAuthProvider()
            isSignedIn = true // the demo is always "signed in"
        }

        let urlString = env["MUNCH_API_URL"] ?? "http://localhost:8123"
        // A malformed override falls back to the demo default rather than
        // crashing at launch — the URL is operator input, not user input.
        let base = URL(string: urlString) ?? URL(string: "http://localhost:8123")!
        api = APIClient(baseURL: base, auth: authProvider)
        homeMetro = UserDefaults.standard.string(forKey: "munch.homeMetro")
        preferredMode = UserDefaults.standard.string(forKey: "munch.preferredMode") ?? "dine_in"
    }

    /// Finish Sign in with Apple: establish the Firebase session, hand the
    /// Apple authorization code to the server for TN3194 token storage, then
    /// admit the user. Errors leave `isSignedIn` false so the screen retries.
    func completeAppleSignIn(
        idToken: String,
        rawNonce: String,
        fullName: PersonNameComponents?,
        appleAuthCode: String?
    ) async {
        guard let firebaseAuth else { return }
        do {
            try await firebaseAuth.completeSignIn(
                idToken: idToken, rawNonce: rawNonce, fullName: fullName
            )
            // TN3194: the server exchanges this single-use code for a refresh
            // token it can later revoke on deletion. Best-effort — a failure
            // here must not block entry (deletion still removes the account).
            if let appleAuthCode {
                try? await api.linkApple(authCode: appleAuthCode)
            }
            isSignedIn = true
        } catch {
            // Leave the gate closed so the screen offers a retry. Log the
            // cause in debug builds — on TestFlight a silent sign-in failure
            // (nonce mismatch, network, invalid token) is otherwise undiagnosable.
            #if DEBUG
                print("Sign in with Apple failed: \(error)")
            #endif
            isSignedIn = false
        }
    }

    /// Account deletion (D-013): server purge + Firebase Admin delete + Apple
    /// token revocation happen server-side; then clear the local session.
    func deleteAccountAndReset() async throws {
        try await api.deleteAccount()
        firebaseAuth?.signOut()
        DemoAuthProvider.reset()
        homeMetro = nil
        UserDefaults.standard.removeObject(forKey: "munch.homeMetro")
        // Demo stays admitted (re-onboards); Firebase returns to the sign-in gate.
        isSignedIn = (firebaseAuth == nil)
    }

    /// Settings "Sign out": clear the session without deleting the account.
    func signOut() {
        firebaseAuth?.signOut()
        homeMetro = nil
        UserDefaults.standard.removeObject(forKey: "munch.homeMetro")
        isSignedIn = (firebaseAuth == nil)
    }
}
