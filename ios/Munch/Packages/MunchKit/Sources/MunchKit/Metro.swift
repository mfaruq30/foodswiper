// The two launch metros. Everything outside NYC + Boston is out of scope for
// v1 (spec §1) — modeling that as a closed enum makes "other cities" a compile
// error rather than a runtime surprise.

/// A launch city.
///
/// The raw values are persisted server-side (`profiles.home_metro`), so they
/// are part of the wire contract — change them only with a database migration.
public enum Metro: String, CaseIterable, Codable, Sendable {
    case nyc
    case boston

    /// Human-readable name for UI display.
    public var displayName: String {
        switch self {
        case .nyc: "New York City"
        case .boston: "Boston"
        }
    }
}
