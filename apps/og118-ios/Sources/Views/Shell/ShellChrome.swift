import SwiftUI

/// El `.fi-aws-toggle` de la web: el único chrome sobre el hilo es este botón
/// flotante de 44×44 que abre el drawer. No hay barra de encabezado.
struct MenuButton: View {
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: "line.3.horizontal")
                .font(.system(size: 18, weight: .medium))
                .foregroundStyle(Theme.textBody)
                .frame(width: 44, height: 44)
                .background(.ultraThinMaterial.opacity(0.35), in: RoundedRectangle(cornerRadius: Theme.menuButtonRadius))
                .background(Theme.menuButtonFill, in: RoundedRectangle(cornerRadius: Theme.menuButtonRadius))
                .overlay(
                    RoundedRectangle(cornerRadius: Theme.menuButtonRadius)
                        .stroke(Theme.menuButtonBorder, lineWidth: 1)
                )
        }
        .accessibilityIdentifier("conversaciones")
        .accessibilityLabel("Conversaciones")
    }
}

/// `watermark-og118.svg` reconstruido con texto: «og118» en negritas sobre «.ai»
/// monoespaciado, a 58% del ancho (tope 280) y al 78% del alto, como la web.
struct Watermark: View {
    var body: some View {
        GeometryReader { geo in
            let ancho = min(geo.size.width * 0.58, 280)
            let escala = ancho / 800
            VStack(spacing: 18 * escala) {
                Text("og118")
                    .font(.system(size: 130 * escala, weight: .bold))
                Text(".ai")
                    .font(.system(size: 30 * escala, design: .monospaced))
                    .tracking(16 * escala)
            }
            .foregroundStyle(Theme.textBody)
            .opacity(Theme.watermarkOpacity)
            .position(x: geo.size.width / 2, y: geo.size.height * 0.78)
        }
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}
