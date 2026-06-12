// Session brain for the swipe deck — the heart of the product (spec §4.2–4.3).
//
// Owns the live card queue, the per-deck request ids (each swipe must join to
// the deck that SERVED its card, D-008), session match state, and prefetch.
// Decision MATH lives in MunchKit (SwipeCommit / MatchPolicy / DeckQueuePolicy);
// this type only sequences it. Event posts are fire-and-forget: a lost swipe
// must never block the next card (spec §4.2.5).

import Foundation
import MunchKit
import Observation

/// View model for `SwipeScreen`: one instance per screen lifetime, holding all
/// state for one swiping session (a mode change starts a fresh session).
@Observable
@MainActor
final class SwipeViewModel {
    /// A match ready to present. `Identifiable` so `.sheet(item:)` can drive
    /// presentation directly off this value.
    struct Match: Identifiable {
        let id = UUID()
        let primary: DeckCard
        let alternates: [DeckCard]
    }

    // MARK: - Observable state

    /// Live queue, front card at index 0. Every card travels with the request
    /// id of the deck that served it — the swipe→deck join key. A single
    /// "current" id would mislabel leftover cards after a prefetch.
    private(set) var queue: [(card: DeckCard, requestId: UUID)] = []
    /// Current discovery mode (tab selection).
    private(set) var mode: SwipeMode = .dineIn
    /// True while the initial/replacing deck fetch runs. Starts true so the
    /// first rendered frame is a spinner, never a flash of empty state.
    private(set) var loading = true
    /// Friendly, presentable failure text; nil when the deck is healthy.
    var errorMessage: String?
    /// Typed empty-deck signal from the server ("no_dietary_matches" | ...).
    private(set) var emptyReason: String?
    /// True when the deck was built from the metro-center fallback location.
    private(set) var usingFallbackLocation = false
    /// Swipe session id — regenerated whenever the mode changes.
    private(set) var sessionId = UUID()
    /// Right-swiped cards this session, in swipe order (MatchPolicy's input).
    private(set) var rightSwipes: [DeckCard] = []
    /// The match sheet's item; non-nil presents `MatchView`.
    var presentedMatch: Match?

    /// Cards-only projection of the queue for the card stack and the states.
    var cards: [DeckCard] {
        queue.map(\.card)
    }

    /// Display name of the active metro, for the location-fallback banner.
    var metroDisplayName: String {
        Metro(rawValue: metroId)?.displayName ?? metroId.capitalized
    }

    // MARK: - Private session plumbing

    private var matchShownThisSession = false
    private var fetchInFlight = false
    /// Every restaurant id enqueued this session — prefetched decks can
    /// overlap, and a card must never be shown twice in one session.
    private var seenIds: Set<String> = []
    private var metroId = "nyc"
    private var lastLocation: UserLocation?
    private var appliedPreferredMode = false

    /// v1 deck search radius in meters (spec §4.2).
    private static let searchRadiusM: Double = 3000

    // MARK: - Loading

    /// First load: resolve a location (with the honest metro-center fallback),
    /// then fetch the deck. Also serves as the retry path after a failure.
    func loadInitial(container: AppContainer) async {
        if !appliedPreferredMode {
            appliedPreferredMode = true
            mode = SwipeMode(rawValue: container.preferredMode) ?? .dineIn
        }
        loading = true
        errorMessage = nil
        metroId = container.homeMetro ?? "nyc"
        let location = await container.location.resolve(metro: metroId)
        usingFallbackLocation = location.isFallback
        lastLocation = location
        await fetchReplacingDeck(container: container)
        loading = false
    }

    /// Append the next deck when the queue runs low. Guarded so only one
    /// prefetch flies at a time; failures stay silent while cards remain.
    func fetchMore(container: AppContainer) async {
        guard !fetchInFlight, let location = lastLocation else { return }
        fetchInFlight = true
        defer { fetchInFlight = false }
        let session = sessionId
        do {
            let deck = try await container.api.getDeck(deckRequest(at: location))
            guard session == sessionId else { return } // stale: mode changed mid-flight
            apply(deck: deck, replacing: false)
        } catch {
            guard session == sessionId else { return }
            // Silent while the user still has cards; surface the failure only
            // when the queue is already dry so the retry button has a job.
            if queue.isEmpty {
                errorMessage = friendlyMessage(for: error)
            }
        }
    }

    // MARK: - Swiping

    /// Commit a swipe on the front card: pop, post (fire-and-forget), match
    /// check, prefetch check. Synchronous on purpose — the UI never waits.
    func swipe(_ direction: SwipeDecision, container: AppContainer) {
        guard direction != .none, !queue.isEmpty else { return }
        let entry = queue.removeFirst()
        let request = SwipeRequest(
            restaurantId: entry.card.restaurantId,
            mode: mode,
            direction: direction == .right ? "right" : "left",
            sessionId: sessionId,
            requestId: entry.requestId,
            cardPosition: entry.card.position,
            explore: entry.card.explore
        )
        let api = container.api
        Task { try? await api.postSwipe(request) }

        if direction == .right {
            rightSwipes.append(entry.card)
            if !matchShownThisSession,
               let match = MatchPolicy.match(rightSwipes: rightSwipes)
            {
                presentedMatch = Match(primary: match.primary, alternates: match.alternates)
                matchShownThisSession = true
            }
        }
        if DeckQueuePolicy.shouldPrefetch(remaining: queue.count, fetchInFlight: fetchInFlight) {
            Task { await fetchMore(container: container) }
        }
    }

    /// Dismiss the match sheet. Right swipes keep accumulating, but only one
    /// match auto-presents per session — no re-popping on the next swipe.
    func keepSwiping() {
        presentedMatch = nil
    }

    /// Switch discovery mode: a brand-new session (id, match state, queue),
    /// then a fresh deck for the new mode.
    func changeMode(_ newMode: SwipeMode, container: AppContainer) async {
        guard newMode != mode else { return }
        mode = newMode
        resetSession()
        loading = true
        errorMessage = nil
        if lastLocation == nil {
            metroId = container.homeMetro ?? "nyc"
            let location = await container.location.resolve(metro: metroId)
            usingFallbackLocation = location.isFallback
            lastLocation = location
        }
        await fetchReplacingDeck(container: container)
        loading = false
    }

    /// Log an outbound CTA tap (fire-and-forget, same rule as swipes).
    func recordConversion(_ type: String, card: DeckCard, container: AppContainer) {
        let request = ConversionRequest(
            restaurantId: card.restaurantId, mode: mode, conversionType: type
        )
        let api = container.api
        Task { try? await api.postConversion(request) }
    }

    // MARK: - Internals

    private func resetSession() {
        sessionId = UUID()
        rightSwipes = []
        matchShownThisSession = false
        presentedMatch = nil
        seenIds = []
        queue = []
        emptyReason = nil
    }

    private func fetchReplacingDeck(container: AppContainer) async {
        guard let location = lastLocation else { return }
        fetchInFlight = true
        defer { fetchInFlight = false }
        let session = sessionId
        do {
            let deck = try await container.api.getDeck(deckRequest(at: location))
            guard session == sessionId else { return }
            apply(deck: deck, replacing: true)
        } catch {
            guard session == sessionId else { return }
            errorMessage = friendlyMessage(for: error)
        }
    }

    private func deckRequest(at location: UserLocation) -> DeckRequest {
        DeckRequest(
            mode: mode, metro: metroId, lat: location.lat, lon: location.lon,
            radiusM: Self.searchRadiusM
        )
    }

    private func apply(deck: Deck, replacing: Bool) {
        // The server's request_id is the swipe join key. A malformed id falls
        // back to a fresh UUID: the join is lost but swiping stays alive.
        let requestId = UUID(uuidString: deck.requestId) ?? UUID()
        if replacing {
            queue = []
            seenIds = []
        }
        let fresh = deck.cards.filter { !seenIds.contains($0.restaurantId) }
        seenIds.formUnion(fresh.map(\.restaurantId))
        queue.append(contentsOf: fresh.map { (card: $0, requestId: requestId) })
        emptyReason = deck.emptyReason
    }

    private func friendlyMessage(for error: Error) -> String {
        guard let apiError = error as? APIError else {
            return "Something went wrong — please try again."
        }
        if case .transport = apiError {
            return "Can't reach the Munch demo server — see DEMO.md"
        }
        return apiError.errorDescription ?? "Something went wrong — please try again."
    }
}
