import SwiftUI

/// El `ComposerActionSlot` de la llamada (`.og-resonance-call-btn`): esmeralda en
/// reposo; en llamada, rojo con «Colgar». En el riel compacto cede la etiqueta.
struct ResonanceCallButton: View {
    let activa: Bool
    let accion: () -> Void

    var body: some View {
        Button(action: accion) {
            Image(systemName: activa ? "phone.down.fill" : "phone")
                .font(.system(size: 17, weight: .regular))
                .foregroundStyle(activa ? Theme.stopText : Theme.accent)
                .frame(width: 44, height: 44)
                .background(Circle().fill(activa ? Theme.resonanceActiveFill : .clear))
                .overlay(Circle().stroke(activa ? Theme.resonanceActiveBorder : Theme.resonanceBorder, lineWidth: 1))
                .contentShape(Circle())
        }
        .accessibilityIdentifier("llamar")
        .accessibilityLabel(activa ? "Colgar la llamada" : "Llamar por voz (Resonance)")
        .accessibilityAddTraits(activa ? .isSelected : [])
    }
}

/// `.og-resonance-live`: en llamada el composer SE VUELVE la superficie de la
/// llamada — ecualizador del micrófono y el estado, encima del texto.
struct ResonanceCallBar: View {
    let estado: ResonanceState
    let bandas: [Double]
    let etiqueta: String?

    private static let barras = ResonancePolicy.bandCount
    private static let alto: CGFloat = 22
    private static let minimo: CGFloat = 4

    var body: some View {
        HStack(spacing: 10) {
            HStack(alignment: .bottom, spacing: 2) {
                ForEach(0..<Self.barras, id: \.self) { i in
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Theme.voiceBar)
                        .frame(width: 3, height: altura(i))
                }
            }
            .frame(minWidth: 80, maxWidth: .infinity, minHeight: Self.alto, maxHeight: Self.alto, alignment: .bottomLeading)
            .animation(.linear(duration: 0.05), value: bandas)
            .accessibilityElement()
            .accessibilityLabel("Nivel de tu voz")
            if let etiqueta {
                Text(etiqueta.uppercased())
                    .font(.system(size: 12))
                    .tracking(0.5)
                    .foregroundStyle(Theme.accentMuted)
                    .lineLimit(1)
                    .fixedSize()
                    .accessibilityIdentifier("estado-llamada")
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
    }

    private func altura(_ i: Int) -> CGFloat {
        guard ResonancePolicy.visualizadorActivo(estado), !bandas.isEmpty else { return Self.minimo }
        let indice = min(bandas.count - 1, Int(Double(i) / Double(Self.barras) * Double(bandas.count)))
        return max(Self.minimo, CGFloat(bandas[indice]) * Self.alto)
    }
}
