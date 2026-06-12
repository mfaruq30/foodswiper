// The onboarding cuisine grid (spec §4.2: ~15 cuisines, 5+ required).
//
// IDs are canonical cuisine nodes from the server's adjacency map — they flow
// straight into ProfileBody.anchorCuisines and must never be display strings.
// Emoji are the placeholder-art language (real photos are absent from open
// data, D-010): each cuisine carries its card identity here, in one place.

public struct Cuisine: Identifiable, Equatable, Sendable {
    public let id: String // canonical node, e.g. "middle_eastern"
    public let displayName: String
    public let emoji: String

    public init(id: String, displayName: String, emoji: String) {
        self.id = id
        self.displayName = displayName
        self.emoji = emoji
    }
}

public enum CuisineCatalog {
    /// The onboarding grid. Order is the display order (broad crowd-pleasers
    /// first). 16 options; the UI requires picking at least 5.
    public static let onboarding: [Cuisine] = [
        Cuisine(id: "pizza", displayName: "Pizza", emoji: "🍕"),
        Cuisine(id: "italian", displayName: "Italian", emoji: "🍝"),
        Cuisine(id: "chinese", displayName: "Chinese", emoji: "🥡"),
        Cuisine(id: "japanese", displayName: "Japanese", emoji: "🍱"),
        Cuisine(id: "sushi", displayName: "Sushi", emoji: "🍣"),
        Cuisine(id: "ramen", displayName: "Ramen", emoji: "🍜"),
        Cuisine(id: "korean", displayName: "Korean", emoji: "🍚"),
        Cuisine(id: "thai", displayName: "Thai", emoji: "🥘"),
        Cuisine(id: "mexican", displayName: "Mexican", emoji: "🌮"),
        Cuisine(id: "burger", displayName: "Burgers", emoji: "🍔"),
        Cuisine(id: "american", displayName: "American", emoji: "🥪"),
        Cuisine(id: "indian", displayName: "Indian", emoji: "🍛"),
        Cuisine(id: "mediterranean", displayName: "Mediterranean", emoji: "🫒"),
        Cuisine(id: "middle_eastern", displayName: "Middle Eastern", emoji: "🧆"),
        Cuisine(id: "seafood", displayName: "Seafood", emoji: "🦞"),
        Cuisine(id: "dessert", displayName: "Dessert", emoji: "🍰"),
    ]

    /// Minimum selections before onboarding may continue (spec §4.2).
    public static let minimumSelection = 5

    /// Display metadata for any canonical cuisine (cards may carry cuisines
    /// outside the onboarding grid — e.g. "cajun"); falls back gracefully.
    public static func display(for id: String) -> (name: String, emoji: String) {
        if let known = onboarding.first(where: { $0.id == id }) {
            return (known.displayName, known.emoji)
        }
        if let extra = extended[id] {
            return extra
        }
        let pretty = id.split(separator: "_").map(\.capitalized).joined(separator: " ")
        return (pretty, "🍽️")
    }

    /// Canonical nodes that appear on cards but not in the onboarding grid.
    static let extended: [String: (name: String, emoji: String)] = [
        "bbq": ("BBQ", "🍖"),
        "bagel": ("Bagels", "🥯"),
        "bakery": ("Bakery", "🥐"),
        "breakfast": ("Breakfast", "🥞"),
        "bubble_tea": ("Bubble Tea", "🧋"),
        "cajun": ("Cajun", "🦐"),
        "caribbean": ("Caribbean", "🍹"),
        "chicken": ("Chicken", "🍗"),
        "coffee": ("Coffee", "☕"),
        "deli": ("Deli", "🥓"),
        "diner": ("Diner", "🍳"),
        "eastern_european": ("Eastern European", "🥟"),
        "ethiopian": ("Ethiopian", "🍲"),
        "filipino": ("Filipino", "🍢"),
        "french": ("French", "🥖"),
        "german": ("German", "🥨"),
        "greek": ("Greek", "🥙"),
        "halal": ("Halal", "🧆"),
        "juice": ("Juice", "🥤"),
        "kosher": ("Kosher", "🥯"),
        "latin": ("Latin", "🫓"),
        "noodles": ("Noodles", "🍜"),
        "pan_asian": ("Pan-Asian", "🥢"),
        "peruvian": ("Peruvian", "🐟"),
        "salad": ("Salads", "🥗"),
        "sandwich": ("Sandwiches", "🥖"),
        "southern": ("Southern", "🍗"),
        "spanish": ("Spanish", "🥘"),
        "steakhouse": ("Steakhouse", "🥩"),
        "turkish": ("Turkish", "🥙"),
        "vegan": ("Vegan", "🌱"),
        "vegetarian": ("Vegetarian", "🥦"),
        "vietnamese": ("Vietnamese", "🍜"),
    ]
}
