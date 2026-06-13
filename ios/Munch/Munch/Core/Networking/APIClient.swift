// Typed HTTP client for the Munch API — an actor wrapping URLSession
// (spec §2: no third-party networking SDK).
//
// The app talks ONLY to this API, never to a database SDK — that is the
// backend-portability seam (D-019). Auth is a bearer token from AuthProviding;
// in the $0 demo that token is a locally generated device id (MUNCH_AUTH=dev
// server mode), and in Phase 6 it becomes a Firebase ID token from Sign in
// with Apple — this client never knows the difference.

import Foundation
import MunchKit

/// Typed failures the UI can present honestly.
enum APIError: Error, LocalizedError {
    case badStatus(Int, body: String)
    case transport(Error)
    case decoding(Error)

    var errorDescription: String? {
        switch self {
        case let .badStatus(code, _): "Server replied \(code)"
        case .transport: "Couldn't reach Munch — check your connection"
        case .decoding: "Unexpected server response"
        }
    }
}

/// The session token source — the auth seam.
protocol AuthProviding: Sendable {
    func currentToken() async throws -> String
}

actor APIClient {
    private let baseURL: URL
    private let auth: AuthProviding
    private let session: URLSession
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    init(baseURL: URL, auth: AuthProviding, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.auth = auth
        self.session = session
    }

    // MARK: - Endpoints (mirror backend/reco/app/main.py exactly)

    func putProfile(_ body: ProfileBody) async throws {
        try await send("PUT", "v1/profile", body: body, expecting: StatusReply.self)
    }

    func getProfile() async throws -> ProfileBody {
        try await send("GET", "v1/profile", body: Empty?.none, expecting: ProfileBody.self)
    }

    func getDeck(_ request: DeckRequest) async throws -> Deck {
        try await send("POST", "v1/deck", body: request, expecting: Deck.self)
    }

    func postSwipe(_ request: SwipeRequest) async throws {
        try await send("POST", "v1/swipes", body: request, expecting: StatusReply.self)
    }

    func postConversion(_ request: ConversionRequest) async throws {
        try await send("POST", "v1/conversions", body: request, expecting: StatusReply.self)
    }

    func search(metro: String, query: String) async throws -> [SearchResult] {
        try await send(
            "GET", "v1/search",
            query: [URLQueryItem(name: "metro", value: metro), URLQueryItem(name: "q", value: query)],
            body: Empty?.none, expecting: [SearchResult].self
        )
    }

    func deleteAccount() async throws {
        try await send("DELETE", "v1/account", body: Empty?.none, expecting: StatusReply.self)
    }

    /// Hand the server the Apple authorization code so it can store a refresh
    /// token for TN3194 revocation at deletion (D-013). Called once at sign-in.
    func linkApple(authCode: String) async throws {
        try await send(
            "POST", "v1/auth/apple-link",
            body: AppleLinkBody(authCode: authCode), expecting: StatusReply.self
        )
    }

    // MARK: - Plumbing

    /// Empty body marker for GET/DELETE.
    private struct Empty: Encodable {}

    /// The {"status": "..."} replies the write endpoints return.
    private struct StatusReply: Decodable {
        let status: String
    }

    @discardableResult
    private func send<Reply: Decodable>(
        _ method: String, _ path: String, query: [URLQueryItem]? = nil,
        body: (some Encodable)?, expecting _: Reply.Type
    ) async throws -> Reply {
        var url = baseURL.appending(path: path)
        if let query, var components = URLComponents(url: url, resolvingAgainstBaseURL: false) {
            components.queryItems = query
            url = components.url ?? url
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let token = try await auth.currentToken()
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        if let body {
            request.httpBody = try encoder.encode(body)
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.transport(error)
        }
        guard let http = response as? HTTPURLResponse else {
            throw APIError.badStatus(0, body: "")
        }
        guard (200 ..< 300).contains(http.statusCode) else {
            throw APIError.badStatus(
                http.statusCode, body: String(data: data, encoding: .utf8) ?? ""
            )
        }
        do {
            return try decoder.decode(Reply.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }
}

/// apple-link body. File-scope (not nested in APIClient) so its CodingKeys
/// snake_case map stays within SwiftLint's type-nesting depth.
private struct AppleLinkBody: Encodable {
    let authCode: String
    enum CodingKeys: String, CodingKey { case authCode = "auth_code" }
}
