// The Munch API wire contract — Codable mirrors of the pydantic models in
// backend/reco/app/main.py. This file IS the client side of the seam (D-019):
// the app never sees Firestore or any backend; it sees these types over HTTP.
//
// Field names match the JSON exactly (snake_case) via CodingKeys so a contract
// drift fails loudly in MunchKitTests' decode fixtures, not silently in the UI.

import Foundation

/// The three discovery modes (mirrors `Mode` server-side).
public enum SwipeMode: String, Codable, CaseIterable, Sendable {
    case dineIn = "dine_in"
    case pickup
    case delivery

    public var displayName: String {
        switch self {
        case .dineIn: "Dine in"
        case .pickup: "Pickup"
        case .delivery: "Delivery"
        }
    }
}

/// One card in a served deck (server `CardResponse`). `lat`/`lon`/`phone`
/// power the conversion CTAs (Apple Maps directions, tel:).
public struct DeckCard: Codable, Identifiable, Equatable, Sendable {
    public let restaurantId: String
    public let name: String
    public let cuisines: [String]
    public let priceTier: Int
    public let priceImputed: Bool
    public let distanceM: Double
    public let lat: Double
    public let lon: Double
    public let phone: String?
    public let reason: String
    public let position: Int
    public let explore: Bool

    public var id: String {
        restaurantId
    }

    enum CodingKeys: String, CodingKey {
        case restaurantId = "restaurant_id"
        case name, cuisines, lat, lon, phone, reason, position, explore
        case priceTier = "price_tier"
        case priceImputed = "price_imputed"
        case distanceM = "distance_m"
    }

    public init(
        restaurantId: String, name: String, cuisines: [String], priceTier: Int,
        priceImputed: Bool, distanceM: Double, lat: Double, lon: Double, phone: String?,
        reason: String, position: Int, explore: Bool
    ) {
        self.restaurantId = restaurantId
        self.name = name
        self.cuisines = cuisines
        self.priceTier = priceTier
        self.priceImputed = priceImputed
        self.distanceM = distanceM
        self.lat = lat
        self.lon = lon
        self.phone = phone
        self.reason = reason
        self.position = position
        self.explore = explore
    }

    /// Distance for display ("0.3 mi") — one formatting rule for every screen.
    public var distanceLabel: String {
        String(format: "%.1f mi", distanceM / 1609.34)
    }
}

/// A served deck (server `DeckResponse`).
public struct Deck: Codable, Equatable, Sendable {
    public let requestId: String
    public let modelVersion: String
    public let cards: [DeckCard]
    /// Typed empty-deck signal (D-022): "no_dietary_matches" | "no_candidates".
    public let emptyReason: String?

    enum CodingKeys: String, CodingKey {
        case cards
        case requestId = "request_id"
        case modelVersion = "model_version"
        case emptyReason = "empty_reason"
    }
}

/// Request body for POST /v1/deck.
public struct DeckRequest: Codable, Sendable {
    public let mode: SwipeMode
    public let metro: String
    public let lat: Double
    public let lon: Double
    public let radiusM: Double

    enum CodingKeys: String, CodingKey {
        case mode, metro, lat, lon
        case radiusM = "radius_m"
    }

    public init(mode: SwipeMode, metro: String, lat: Double, lon: Double, radiusM: Double) {
        self.mode = mode
        self.metro = metro
        self.lat = lat
        self.lon = lon
        self.radiusM = radiusM
    }
}

/// Request body for POST /v1/swipes. `requestId` is the deck join key and
/// `explore` the exploration label — both REQUIRED by the server (D-008).
public struct SwipeRequest: Codable, Sendable {
    public let restaurantId: String
    public let mode: SwipeMode
    public let direction: String // "left" | "right"
    public let sessionId: UUID
    public let requestId: UUID
    public let cardPosition: Int
    public let explore: Bool

    enum CodingKeys: String, CodingKey {
        case mode, direction, explore
        case restaurantId = "restaurant_id"
        case sessionId = "session_id"
        case requestId = "request_id"
        case cardPosition = "card_position"
    }

    public init(
        restaurantId: String, mode: SwipeMode, direction: String, sessionId: UUID,
        requestId: UUID, cardPosition: Int, explore: Bool
    ) {
        self.restaurantId = restaurantId
        self.mode = mode
        self.direction = direction
        self.sessionId = sessionId
        self.requestId = requestId
        self.cardPosition = cardPosition
        self.explore = explore
    }
}

/// Request body for POST /v1/conversions (an outbound tap, honestly named).
public struct ConversionRequest: Codable, Sendable {
    public let restaurantId: String
    public let mode: SwipeMode
    public let conversionType: String

    enum CodingKeys: String, CodingKey {
        case mode
        case restaurantId = "restaurant_id"
        case conversionType = "conversion_type"
    }

    public init(restaurantId: String, mode: SwipeMode, conversionType: String) {
        self.restaurantId = restaurantId
        self.mode = mode
        self.conversionType = conversionType
    }
}

/// PUT/GET /v1/profile body.
public struct ProfileBody: Codable, Equatable, Sendable {
    public var displayName: String?
    public var homeMetro: String?
    public var anchorCuisines: [String]
    public var cuisineWeights: [String: Double]
    public var pricePref: Int?
    public var dietaryFlags: [String]

    enum CodingKeys: String, CodingKey {
        case displayName = "display_name"
        case homeMetro = "home_metro"
        case anchorCuisines = "anchor_cuisines"
        case cuisineWeights = "cuisine_weights"
        case pricePref = "price_pref"
        case dietaryFlags = "dietary_flags"
    }

    public init(
        displayName: String? = nil, homeMetro: String? = nil, anchorCuisines: [String] = [],
        cuisineWeights: [String: Double] = [:], pricePref: Int? = nil, dietaryFlags: [String] = []
    ) {
        self.displayName = displayName
        self.homeMetro = homeMetro
        self.anchorCuisines = anchorCuisines
        self.cuisineWeights = cuisineWeights
        self.pricePref = pricePref
        self.dietaryFlags = dietaryFlags
    }
}

/// GET /v1/search result row (onboarding anchor autocomplete).
public struct SearchResult: Codable, Identifiable, Equatable, Sendable {
    public let restaurantId: String
    public let name: String
    public let cuisines: [String]

    public var id: String {
        restaurantId
    }

    enum CodingKeys: String, CodingKey {
        case name, cuisines
        case restaurantId = "restaurant_id"
    }

    public init(restaurantId: String, name: String, cuisines: [String]) {
        self.restaurantId = restaurantId
        self.name = name
        self.cuisines = cuisines
    }
}
