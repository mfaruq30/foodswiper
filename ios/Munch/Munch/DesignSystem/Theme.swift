// Munch design tokens — the approved prototype's aesthetic as code:
// warm paper background, editorial serif display (Fraunces, OFL — bundled),
// refined sans body (SF Pro), confident warm-orange accent.
//
// Every color/space/radius in the app comes from here; a magic number in a
// view is a review failure (spec §4.4).

import SwiftUI

enum Theme {
    // MARK: - Color tokens (hex values are the design-system source of truth)

    /// Warm paper — the app's canvas. NOT pure white on purpose.
    static let paper = Color(hex: 0xFAF6F0)
    /// Card surface: a half-step brighter than paper so cards lift.
    static let surface = Color(hex: 0xFFFDF9)
    /// Primary ink for display + body text.
    static let ink = Color(hex: 0x2B2118)
    /// Secondary text: captions, metadata.
    static let inkSecondary = Color(hex: 0x6E5F51)
    /// The confident warm orange — CTAs, selection, the brand moment.
    static let accent = Color(hex: 0xE8552E)
    /// Soft tint of the accent for chips/selected states.
    static let accentSoft = Color(hex: 0xFBE3DB)
    /// "Yes" swipe affirmation.
    static let yes = Color(hex: 0x2E8B57)
    /// "Nope" swipe rejection.
    static let nope = Color(hex: 0xC0392B)
    /// Hairlines and card borders.
    static let stroke = Color(hex: 0xE8DFD3)

    // MARK: - Spacing scale (pt) — use these, never ad-hoc values

    static let space2: CGFloat = 4
    static let space3: CGFloat = 8
    static let space4: CGFloat = 12
    static let space5: CGFloat = 16
    static let space6: CGFloat = 24
    static let space7: CGFloat = 32
    static let space8: CGFloat = 48

    // MARK: - Radii / elevation

    static let radiusCard: CGFloat = 24
    static let radiusControl: CGFloat = 14
    static let radiusChip: CGFloat = 999 // capsule

    /// The one card shadow, used everywhere a card lifts off the paper.
    static func cardShadow(_ content: some View) -> some View {
        content.shadow(color: ink.opacity(0.10), radius: 18, x: 0, y: 8)
    }
}

// MARK: - Typography

extension Font {
    /// Editorial serif display — Fraunces (SIL OFL, bundled in Resources/Fonts).
    /// Falls back to the system serif design if the custom font fails to
    /// register, so a font pipeline problem can never blank the UI.
    static func display(_ size: CGFloat) -> Font {
        if UIFont(name: "Fraunces", size: size) != nil {
            return .custom("Fraunces", size: size)
        }
        return .system(size: size, design: .serif).weight(.semibold)
    }

    /// Body/sans roles use the native SF stack (the "refined sans"): keep
    /// Dynamic Type behavior by mapping to text styles, not fixed sizes.
    static let munchTitle = display(34)
    static let munchHeading = display(24)
    static let munchCardName = display(28)
}

extension Color {
    /// Hex literal initializer so token values read like the design sheet.
    init(hex: UInt32) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255,
            opacity: 1
        )
    }
}
