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

/// Espejo nativo del preset glass-chat de fi-glass (`glass-chat-preset.ts` +
/// `messages/styles.ts`). Los literales vienen de ahí: si la web cambia un
/// token, éste es el archivo que se re-sincroniza.
enum Theme {
    static let bgDeep = Color(hex: 0x020617)
    static let bgMid = Color(hex: 0x0F172A)
    static let accent = Color(hex: 0x34D399)
    static let accentDeep = Color(hex: 0x059669)
    static let accentMuted = Color(hex: 0xA3A3A3)
    static let danger = Color(hex: 0xF87171)
    static let text = Color.white
    static let textBody = Color(hex: 0xE2E8F0)
    static let textMuted = Color(hex: 0x94A3B8)
    static let textFaint = Color(hex: 0x64748B)
    static let surface = Color(hex: 0x1E293B).opacity(0.6)
    static let surfaceBorder = Color(hex: 0x475569).opacity(0.4)
    static let bubbleUser = Color(hex: 0x059669).opacity(0.32)
    static let bubbleUserBorder = Color(hex: 0x34D399).opacity(0.25)
    static let bubbleAssistant = Color(hex: 0x1E293B).opacity(0.55)
    static let bubbleBorder = Color(hex: 0x475569).opacity(0.35)
    static let glow = Color(hex: 0x0891B2).opacity(0.07)
    static let radius: CGFloat = 16

    static let authorUser = Color(hex: 0x7C3AED).opacity(0.8)
    static let authorAgentText = Color(hex: 0x0A0F1E)
    static let authorName = Color(hex: 0xCBD5E1)

    static let typingDot = Color(hex: 0xFBBF24).opacity(0.8)
    static let codeInline = Color(hex: 0xFCD34D).opacity(0.9)
    static let codeBlockBg = Color(hex: 0x0F172A).opacity(0.8)
    static let codeBlockBorder = Color(hex: 0x334155).opacity(0.3)
    static let quoteBg = Color.white.opacity(0.03)
    static let quoteAccent = Color(hex: 0xF59E0B).opacity(0.6)

    static let chipBorder = Color(hex: 0x10B981).opacity(0.3)
    static let chipFill = Color.white.opacity(0.05)
    static let itemSelectedBg = Color(hex: 0x34D399).opacity(0.08)
    static let itemSelectedBorder = Color(hex: 0x34D399).opacity(0.3)
    static let itemHover = Color.white.opacity(0.04)
    static let itemMeta = Color(hex: 0x475569)
    static let itemAction = Color(hex: 0x64748B)
    static let sidebarDivider = Color.white.opacity(0.06)
    static let searchFill = Color.white.opacity(0.04)
    static let searchBorder = Color.white.opacity(0.1)

    static let badgeSelected = Color(hex: 0x10B981).opacity(0.3)
    static let badgeSelectedText = Color(hex: 0xD1FAE5)
    static let engineChipFill = Color(hex: 0x10B981).opacity(0.1)
    static let archiveSwipe = Color(hex: 0x475569)

    static let sendText = Color(hex: 0x052E1A)
    static let sendDisabledBorder = Color(hex: 0x94A3B8).opacity(0.28)
    static let stopFill = Color(hex: 0xDC2626).opacity(0.9)
    static let stopBorder = Color(hex: 0xF87171).opacity(0.6)
    static let stopText = Color(hex: 0xFEE2E2)

    static var sendGradient: LinearGradient {
        LinearGradient(
            colors: [accent, accentDeep],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
    }
}

/// La marca «og118.ai»: blanco + esmeralda, el mismo par que el logo web.
struct Wordmark: View {
    let size: CGFloat

    var body: some View {
        Text("og118")
            .font(.system(size: size, weight: .bold))
            .foregroundStyle(Theme.text)
        + Text(".ai")
            .font(.system(size: size, weight: .bold))
            .foregroundStyle(Theme.accent)
    }
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
