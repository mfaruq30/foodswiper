// Pre-fetch policy: a swipe must never wait on the network (spec §4.2.5).
// Pure threshold logic so the rule is tested, not vibes in a view model.

public enum DeckQueuePolicy {
    /// When this few unswiped cards remain, fetch the next deck.
    public static let prefetchThreshold = 4

    /// True when the view model should kick off the next deck request.
    public static func shouldPrefetch(remaining: Int, fetchInFlight: Bool) -> Bool {
        remaining <= prefetchThreshold && !fetchInFlight
    }
}
