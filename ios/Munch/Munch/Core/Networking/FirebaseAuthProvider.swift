// Sign in with Apple -> Firebase session, behind the AuthProviding seam.
//
// Only the handful of Firebase API calls are gated on `canImport(FirebaseAuth)`
// (a release build links it — docs/RELEASE.md). Everything else, including the
// conformance, compiles in every build, so the demo/CI build that omits
// Firebase still type-checks this file — it simply never selects this provider
// (AppContainer picks DemoAuthProvider when Firebase is not configured).

import Foundation

#if canImport(FirebaseAuth)
    import FirebaseAuth
#endif

enum SignInError: Error, LocalizedError {
    case firebaseUnavailable
    case notSignedIn

    var errorDescription: String? {
        switch self {
        case .firebaseUnavailable: "Sign-in isn't available in this build."
        case .notSignedIn: "You're not signed in."
        }
    }
}

struct FirebaseAuthProvider: AuthProviding {
    /// A fresh Firebase ID token for the Authorization header. Firebase
    /// refreshes the underlying token automatically; this never blocks the UI.
    func currentToken() async throws -> String {
        #if canImport(FirebaseAuth)
            guard let user = Auth.auth().currentUser else { throw SignInError.notSignedIn }
            return try await user.getIDToken()
        #else
            throw SignInError.firebaseUnavailable
        #endif
    }

    /// Returning users are already signed in (Firebase persists the session) —
    /// this drives the launch-time "skip the sign-in screen" auto sign-in.
    var isSignedIn: Bool {
        #if canImport(FirebaseAuth)
            return Auth.auth().currentUser != nil
        #else
            return false
        #endif
    }

    /// Exchange a verified Apple credential for a Firebase session.
    func completeSignIn(
        idToken: String, rawNonce: String, fullName: PersonNameComponents?
    ) async throws {
        #if canImport(FirebaseAuth)
            let credential = OAuthProvider.appleCredential(
                withIDToken: idToken, rawNonce: rawNonce, fullName: fullName
            )
            _ = try await Auth.auth().signIn(with: credential)
        #else
            throw SignInError.firebaseUnavailable
        #endif
    }

    func signOut() {
        #if canImport(FirebaseAuth)
            try? Auth.auth().signOut()
        #endif
    }

    // No client-side deleteUser(): account deletion goes through the server
    // (DELETE /v1/account), which removes the Firebase user via the Admin SDK
    // and revokes the Apple refresh token (TN3194). The client only signs out
    // afterward (AppContainer.deleteAccountAndReset) — a redundant local
    // currentUser.delete() would just risk an error after the account is gone.
}
