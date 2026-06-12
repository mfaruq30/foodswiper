// State + submit logic for the whole onboarding flow. One view model spans
// all steps so cuisines, anchors, metro, and mode land in a single
// PUT /v1/profile at the end — the server never sees a partial profile.

import Foundation
import MunchKit
import Observation

/// Drives onboarding: cuisine picks, anchor restaurant search/selection,
/// metro, mode, and the final profile submission.
@Observable
@MainActor
final class OnboardingViewModel {
    /// Most anchors a user may pick (more adds noise, not signal).
    static let anchorLimit = 5
    /// Cap on anchor_cuisines sent to the server (wire-contract bound).
    static let cuisineSendLimit = 20
    /// Minimum query length before we bother the search endpoint.
    static let minimumQueryLength = 2

    var selectedCuisines: Set<String> = []
    var metro: Metro = .nyc
    var anchors: [SearchResult] = []
    var searchQuery = ""
    var searchResults: [SearchResult] = []
    var searching = false
    var mode: SwipeMode = .dineIn
    var submitting = false
    var errorMessage: String?

    /// The cuisine step may continue once the minimum picks are in.
    var canContinueCuisines: Bool {
        selectedCuisines.count >= CuisineCatalog.minimumSelection
    }

    /// Runs a metro-scoped restaurant search. Failures are non-fatal — anchors
    /// are optional, so an error simply reads as "no results" in the UI.
    func runSearch(container: AppContainer) async {
        let query = searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        guard query.count >= Self.minimumQueryLength else {
            searchResults = []
            return
        }
        searching = true
        defer { searching = false }
        do {
            searchResults = try await container.api.search(metro: metro.rawValue, query: query)
        } catch {
            // A cancelled task means a newer query took over — don't clobber it.
            guard !Task.isCancelled else { return }
            searchResults = []
        }
    }

    /// Adds or removes an anchor pick, capped at `anchorLimit`.
    func toggleAnchor(_ result: SearchResult) {
        if let index = anchors.firstIndex(where: { $0.id == result.id }) {
            anchors.remove(at: index)
        } else if anchors.count < Self.anchorLimit {
            anchors.append(result)
        }
    }

    /// Whether a search result is currently picked as an anchor.
    func isAnchored(_ result: SearchResult) -> Bool {
        anchors.contains { $0.id == result.id }
    }

    /// Saves the assembled profile. On success the container's `homeMetro`
    /// flips non-nil, which is the signal the root coordinator uses to exit
    /// onboarding; `preferredMode` is set first so the deck opens correctly.
    func submit(container: AppContainer) async {
        guard !submitting else { return }
        submitting = true
        errorMessage = nil
        defer { submitting = false }
        let body = ProfileBody(
            homeMetro: metro.rawValue,
            anchorCuisines: anchorCuisineIDs,
            pricePref: nil,
            dietaryFlags: []
        )
        do {
            try await container.api.putProfile(body)
            container.preferredMode = mode.rawValue
            container.homeMetro = metro.rawValue
        } catch {
            errorMessage = "Couldn't save — is the demo server running?"
        }
    }

    /// Selected cuisine IDs plus each anchor's first cuisine, deduped and
    /// capped. Selections are sorted so the payload is deterministic.
    private var anchorCuisineIDs: [String] {
        var ids = selectedCuisines.sorted()
        for anchor in anchors {
            guard let first = anchor.cuisines.first else { continue }
            if !ids.contains(first) {
                ids.append(first)
            }
        }
        return Array(ids.prefix(Self.cuisineSendLimit))
    }
}
