// One-shot location with an honest fallback.
//
// Munch needs a coordinate to build a deck. If the user grants
// when-in-use access we use the real fix; if they decline (or the simulator
// has none) we fall back to the selected metro's center and SAY SO in the UI
// — never a silent fake location. Each metro's preset is a real, dense spot
// so the demo deck is always good.

import CoreLocation
import Foundation

struct UserLocation: Equatable {
    let lat: Double
    let lon: Double
    /// True when this is the metro-center fallback, not a device fix.
    let isFallback: Bool
}

enum MetroPresets {
    /// Washington Square Park — the densest seed-venue area in NYC.
    static let nyc = (lat: 40.7308, lon: -73.9973)
    /// BU East Campus — surrounded by seeded venues.
    static let boston = (lat: 42.3505, lon: -71.1054)

    static func center(for metro: String) -> (lat: Double, lon: Double) {
        metro == "boston" ? boston : nyc
    }
}

@MainActor
final class LocationProvider: NSObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()
    private var continuation: CheckedContinuation<CLLocation?, Never>?

    /// Request a single fix; nil when denied/unavailable (caller falls back).
    func requestOnce() async -> CLLocation? {
        let status = manager.authorizationStatus
        if status == .denied || status == .restricted {
            return nil
        }
        if status == .notDetermined {
            manager.requestWhenInUseAuthorization()
        }
        return await withCheckedContinuation { continuation in
            self.continuation = continuation
            manager.delegate = self
            manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
            manager.requestLocation()
        }
    }

    func resolve(metro: String) async -> UserLocation {
        if let fix = await requestOnce() {
            return UserLocation(
                lat: fix.coordinate.latitude, lon: fix.coordinate.longitude, isFallback: false
            )
        }
        let preset = MetroPresets.center(for: metro)
        return UserLocation(lat: preset.lat, lon: preset.lon, isFallback: true)
    }

    nonisolated func locationManager(
        _ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]
    ) {
        Task { @MainActor in
            continuation?.resume(returning: locations.first)
            continuation = nil
        }
    }

    nonisolated func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        Task { @MainActor in
            continuation?.resume(returning: nil)
            continuation = nil
        }
    }
}
