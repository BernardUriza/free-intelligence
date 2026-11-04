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

/// Espejo nativo del preset glass-chat de fi-glass — pero ya NO transcrito a
/// mano: los valores viven en el contrato
/// `free-intelligence-core/contracts/glass-chat-tokens.json` y llegan aquí por
/// `Generated/Theme.generated.swift` (gen:swift-theme). Este archivo conserva
/// sólo lo que un contrato de datos no puede expresar: el helper de color y la
/// composición (gradientes, fondo, estilos de botón).
enum Theme {
    /// El gradiente del botón de enviar: el mismo par que la web
    /// (`linear-gradient(135deg, --og-accent, #059669)` en .og-send-btn).
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
    var weight: Font.Weight = .bold

    var body: some View {
        Text("og118")
            .font(.system(size: size, weight: weight))
            .foregroundStyle(Theme.text)
        + Text(".ai")
            .font(.system(size: size, weight: weight))
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

/// Liquid Glass para lo que FLOTA sobre el hilo (barra, píldora, chips), nunca
/// para el contenido. En iOS 18–25 cae a material con el borde del preset.
struct FiGlass<Forma: Shape>: ViewModifier {
    let forma: Forma
    var interactivo = false

    func body(content: Content) -> some View {
        if #available(iOS 26, *) {
            content.glassEffect(interactivo ? .regular.interactive() : .regular, in: forma)
        } else {
            content
                .background(.ultraThinMaterial, in: forma)
                .overlay(forma.stroke(Theme.surfaceBorder, lineWidth: 1))
        }
    }
}

extension View {
    func fiGlass<Forma: Shape>(in forma: Forma, interactivo: Bool = false) -> some View {
        modifier(FiGlass(forma: forma, interactivo: interactivo))
    }
}

/// Botón redondo de vidrio de 44 pt: el idioma de la barra superior.
struct GlassCircleButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 17, weight: .medium))
            .foregroundStyle(Theme.textBody)
            .frame(width: 44, height: 44)
            .contentShape(Circle())
            .fiGlass(in: Circle(), interactivo: true)
            .opacity(configuration.isPressed ? 0.7 : 1)
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
