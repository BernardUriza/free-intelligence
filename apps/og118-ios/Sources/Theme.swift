import SwiftUI

extension Color {
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

enum Theme {
    static let bgDeep = Color(hex: 0x0A0E16)
    static let bgMid = Color(hex: 0x0F172A)
    static let accent = Color(hex: 0x34D399)
    static let accentMuted = Color(hex: 0xA3A3A3)
    static let danger = Color(hex: 0xF87171)
    static let text = Color.white
    static let textMuted = Color(hex: 0x94A3B8)
    static let surface = Color(hex: 0x1E293B).opacity(0.6)
    static let surfaceBorder = Color(hex: 0x475569).opacity(0.4)
    static let bubbleUser = Color(hex: 0x059669).opacity(0.32)
    static let bubbleUserBorder = Color(hex: 0x34D399).opacity(0.25)
    static let bubbleAssistant = Color(hex: 0x1E293B).opacity(0.55)
    static let bubbleBorder = Color(hex: 0x475569).opacity(0.35)
    static let glow = Color(hex: 0x34D399).opacity(0.06)
    static let radius: CGFloat = 16
}

struct GlassBackground: View {
    var body: some View {
        LinearGradient(
            colors: [Theme.bgDeep, Theme.bgMid, Theme.bgDeep],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        .overlay(alignment: .topTrailing) {
            RadialGradient(
                colors: [Theme.glow, .clear],
                center: .center,
                startRadius: 0,
                endRadius: 420
            )
            .frame(width: 840, height: 840)
            .offset(x: 180, y: -180)
            .allowsHitTesting(false)
        }
        .ignoresSafeArea()
    }
}

struct AccentButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundStyle(Theme.bgDeep)
            .padding(.vertical, 14)
            .padding(.horizontal, 28)
            .background(Theme.accent.opacity(configuration.isPressed ? 0.8 : 1))
            .clipShape(Capsule())
    }
}
