// App entry point + the thin root coordinator (spec §2: MVVM with a thin
// coordinator — routing decisions live here and nowhere else).

import MunchKit
import SwiftUI

@main
struct MunchApp: App {
    @State private var container = AppContainer()

    var body: some Scene {
        WindowGroup {
            RootCoordinatorView()
                .environment(container)
                .tint(Theme.accent)
                .background(Theme.paper)
        }
    }
}

/// Routes between onboarding and the main app — the only place that decides
/// "which world is the user in".
struct RootCoordinatorView: View {
    @Environment(AppContainer.self) private var container

    var body: some View {
        if container.homeMetro == nil {
            OnboardingFlowView()
        } else {
            MainTabView()
        }
    }
}

/// The signed-in shell: Swipe is the product; Profile is the utility drawer.
struct MainTabView: View {
    var body: some View {
        TabView {
            SwipeScreen()
                .tabItem { Label("Munch", systemImage: "flame.fill") }
            ProfileScreen()
                .tabItem { Label("Profile", systemImage: "person.crop.circle") }
        }
    }
}
