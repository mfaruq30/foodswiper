// swift-tools-version: 5.10
// MunchKit — platform-independent domain logic for Munch.
//
// Why a separate SwiftPM package: pure logic (scoring helpers, gesture-commit
// math, domain models) lives here so it can be unit-tested with `swift test`
// on Linux CI — and on the Windows dev machine — without the iOS SDK.
// Anything importing SwiftUI/UIKit belongs in the app target, not here.
import PackageDescription

let package = Package(
    name: "MunchKit",
    platforms: [
        .iOS(.v17),
        .macOS(.v14), // lets the package build/test on macOS CI runners directly
    ],
    products: [
        .library(name: "MunchKit", targets: ["MunchKit"]),
    ],
    targets: [
        .target(name: "MunchKit"),
        .testTarget(name: "MunchKitTests", dependencies: ["MunchKit"]),
    ]
)
