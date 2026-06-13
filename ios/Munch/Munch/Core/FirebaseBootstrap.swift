// Firebase initialization — runtime-optional by design (D-019 / D-024 spirit).
//
// Firebase configures ONLY when both are true: the FirebaseCore SDK is linked
// (a release build adds it — see docs/RELEASE.md) AND a GoogleService-Info.plist
// is bundled. Neither holds in the $0 demo or in CI, so Firebase stays dormant
// and the app falls back to DemoAuthProvider with Sign in with Apple bypassed.
// That single rule is what keeps the demo and the ios-e2e gate green without a
// Firebase project, while a real TestFlight build gets full Sign in with Apple.

import Foundation

#if canImport(FirebaseCore)
    import FirebaseCore
#endif

enum FirebaseBootstrap {
    /// Configure Firebase if the SDK is present and a config plist is bundled.
    /// Returns whether Firebase is now active (drives the auth-provider choice).
    @discardableResult
    static func configureIfAvailable() -> Bool {
        #if canImport(FirebaseCore)
            guard Bundle.main.url(forResource: "GoogleService-Info", withExtension: "plist") != nil
            else {
                return false // no config => demo mode
            }
            if FirebaseApp.app() == nil {
                FirebaseApp.configure()
            }
            return true
        #else
            return false // SDK not linked (demo/CI build)
        #endif
    }

    /// True once Firebase has been configured this launch.
    static var isConfigured: Bool {
        #if canImport(FirebaseCore)
            return FirebaseApp.app() != nil
        #else
            return false
        #endif
    }
}
