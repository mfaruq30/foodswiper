// Profile-tab state: loads/edits the server profile and runs account
// deletion (D-013, Apple 5.1.1(v)). Dietary toggles save optimistically and
// revert on failure so the chips never show a state the server didn't keep.

import Foundation
import MunchKit
import Observation

@Observable
@MainActor
final class ProfileViewModel {
    /// The server profile; nil until the first load resolves.
    var profile: ProfileBody?
    /// True while a profile fetch is in flight.
    var loading = false
    /// Human-readable failure for the UI; nil when healthy.
    var errorMessage: String?
    /// True while account deletion is in flight (replaces the delete row).
    var deleting = false

    /// Fetch the profile. A 404 is NOT an error: it means this identity has
    /// no server profile yet, so the screen starts from an empty editable one.
    func load(container: AppContainer) async {
        loading = true
        errorMessage = nil
        do {
            profile = try await container.api.getProfile()
        } catch APIError.badStatus(404, _) {
            // No profile server-side yet — seed with the locally chosen metro
            // so a later save doesn't blank what onboarding established.
            profile = ProfileBody(homeMetro: container.homeMetro)
        } catch {
            errorMessage = error.localizedDescription
        }
        loading = false
    }

    /// Optimistic toggle: flip locally first (instant chip feedback), then
    /// save; revert the flip if the save fails so UI and server agree.
    func toggleDietary(_ flag: String, container: AppContainer) async {
        guard var updated = profile else { return }
        let original = updated
        if let index = updated.dietaryFlags.firstIndex(of: flag) {
            updated.dietaryFlags.remove(at: index)
        } else {
            updated.dietaryFlags.append(flag)
        }
        profile = updated
        do {
            try await container.api.putProfile(updated)
        } catch {
            profile = original
            errorMessage = "Couldn't save that change. \(error.localizedDescription)"
        }
    }

    /// Run the full account purge (server first, then local identity).
    /// On success the root coordinator routes back to onboarding by itself,
    /// because the purge clears the persisted home metro.
    func deleteAccount(container: AppContainer) async -> Bool {
        deleting = true
        defer { deleting = false }
        do {
            try await container.deleteAccountAndReset()
            return true
        } catch {
            errorMessage = "Deletion didn't complete. \(error.localizedDescription)"
            return false
        }
    }
}
