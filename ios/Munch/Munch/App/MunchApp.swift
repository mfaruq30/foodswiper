// App entry point.
//
// Phase 0 ships a deliberate placeholder view: the real root (coordinator →
// onboarding/swipe) arrives in Phase 4. The target exists now so the macOS CI
// pipeline (xcodegen → xcodebuild) is proven before feature code depends on it.

import MunchKit
import SwiftUI

@main
struct MunchApp: App {
    var body: some Scene {
        WindowGroup {
            // FUTURE(Phase 4): replace with AppCoordinator's root view.
            VStack(spacing: 8) {
                Text("Munch")
                    .font(.largeTitle.bold())
                Text(Metro.allCases.map(\.displayName).joined(separator: " · "))
                    .font(.footnote)
            }
        }
    }
}
