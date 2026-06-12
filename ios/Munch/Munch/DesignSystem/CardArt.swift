// Placeholder card art — a FIRST-CLASS design element, not a fallback.
//
// Open data has effectively zero restaurant photos (~0.04% of POIs, D-010),
// so the cuisine-keyed gradient + emoji treatment IS the product's visual
// identity at launch. Deterministic per venue: the same restaurant always
// renders the same art (hash of its id picks the gradient variant), so cards
// feel stable across decks and sessions.

import MunchKit
import SwiftUI

struct CardArt: View {
    let venueId: String
    let cuisine: String

    var body: some View {
        let palette = Self.palette(for: cuisine, seed: venueId)
        let display = CuisineCatalog.display(for: cuisine)
        ZStack {
            LinearGradient(
                colors: [palette.0, palette.1],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            Text(display.emoji)
                .font(.system(size: 96))
                .opacity(0.9)
                .accessibilityHidden(true)
        }
        .accessibilityLabel("\(display.name) restaurant")
    }

    /// Cuisine family -> warm gradient pair; venue id hash picks one of two
    /// variants so adjacent same-cuisine cards don't look like clones.
    static func palette(for cuisine: String, seed: String) -> (Color, Color) {
        let variant = abs(seed.hashValue) % 2
        let base: [(Color, Color)] = family(for: cuisine)
        return base[variant % base.count]
    }

    private static func family(for cuisine: String) -> [(Color, Color)] {
        switch cuisine {
        case "pizza", "italian", "mediterranean":
            [(Color(hex: 0xF2A65A), Color(hex: 0xE8552E)), (Color(hex: 0xF7C59F), Color(hex: 0xD7263D))]
        case "japanese", "sushi", "ramen", "korean", "chinese", "pan_asian", "noodles",
             "vietnamese", "thai", "filipino":
            [(Color(hex: 0xF67B45), Color(hex: 0x9B2226)), (Color(hex: 0xFFB385), Color(hex: 0xBC4749))]
        case "mexican", "latin", "caribbean", "peruvian", "spanish":
            [(Color(hex: 0xF9C74F), Color(hex: 0xF3722C)), (Color(hex: 0xF8961E), Color(hex: 0xD62828))]
        case "vegan", "vegetarian", "salad", "juice":
            [(Color(hex: 0xB5C99A), Color(hex: 0x55828B)), (Color(hex: 0xCFE1B9), Color(hex: 0x718355))]
        case "coffee", "bakery", "dessert", "breakfast", "bagel", "bubble_tea":
            [(Color(hex: 0xE6CCB2), Color(hex: 0x9C6644)), (Color(hex: 0xF1DCA7), Color(hex: 0xB08968))]
        case "seafood":
            [(Color(hex: 0x90C2E7), Color(hex: 0x3E7CB1)), (Color(hex: 0xA9D6E5), Color(hex: 0x2A6F97))]
        default:
            [(Color(hex: 0xF2A65A), Color(hex: 0xBC6C25)), (Color(hex: 0xF7B267), Color(hex: 0x99582A))]
        }
    }
}
