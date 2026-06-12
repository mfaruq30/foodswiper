// When does swiping become a MATCH? Pure policy, unit-tested.
//
// Product behavior (spec §1): after a few right-swipes the app stops the deck
// and confidently presents the best one. v1 policy: the Nth right-swipe in a
// session triggers the match; the presented match is the highest-ranked
// right-swiped card (deck order IS the ranker's order), the alternates are
// the other right-swipes. Honest and simple — no fake "confidence" math on
// top of a ranking the server already did.

import Foundation

public enum MatchPolicy {
    /// Right-swipes in one session needed before a match is presented.
    public static let rightSwipesToMatch = 3

    /// Given the session's right-swiped cards (in swipe order), return the
    /// match and up to two alternates once the threshold is met, else nil.
    public static func match(rightSwipes: [DeckCard]) -> (primary: DeckCard, alternates: [DeckCard])? {
        guard rightSwipes.count >= rightSwipesToMatch else { return nil }
        // Lowest deck position = ranked best by the server.
        let ranked = rightSwipes.sorted { $0.position < $1.position }
        guard let primary = ranked.first else { return nil }
        return (primary, Array(ranked.dropFirst().prefix(2)))
    }
}
