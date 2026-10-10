import SwiftUI

/// `Og118StartScreen` de la web: la casilla del oganesón, el wordmark y el copy
/// en español, arriba del hilo y no centrada — así cae en app.og118.ai.
struct StartCard: View {
    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                Image("OgTile")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 156)
                    .accessibilityLabel("Oganesón, elemento 118")
                Wordmark(size: 26, weight: .regular)
                    .tracking(-0.5)
                    .padding(.top, 16)
                Text("Og · 118 · Oganesón: sintético, el más pesado que se conoce, el final de la tabla.")
                    .font(.system(size: 14))
                    .foregroundStyle(Theme.textMuted)
                    .lineSpacing(3)
                    .padding(.top, 4)
                Text("Un compañero para pensar, sobre el sustrato de Free Intelligence. Caja de cristal por diseño: ves el razonamiento, no sólo la respuesta.")
                    .font(.system(size: 15))
                    .foregroundStyle(Theme.authorName)
                    .lineSpacing(6)
                    .padding(.top, 16)
                (Text("Escribe abajo, dicta con el micrófono o toca ")
                    + Text("Llamar").fontWeight(.semibold).foregroundStyle(Theme.accent)
                    + Text(" para hablar en voz."))
                    .font(.system(size: 14))
                    .foregroundStyle(Theme.textMuted)
                    .lineSpacing(3)
                    .padding(.top, 24)
            }
            .multilineTextAlignment(.center)
            .fixedSize(horizontal: false, vertical: true)
            .padding(.vertical, 24)
            .padding(.horizontal, 18)
            .frame(maxWidth: .infinity)
            .background(Theme.bgMid.opacity(0.55), in: RoundedRectangle(cornerRadius: Theme.radius))
            .overlay(
                RoundedRectangle(cornerRadius: Theme.radius)
                    .stroke(Theme.startCardBorder, lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.45), radius: 30, y: 20)
            .padding(.horizontal, 12)
            .padding(.top, 60)
        }
        .scrollBounceBehavior(.basedOnSize)
    }
}
