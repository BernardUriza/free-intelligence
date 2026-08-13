import SwiftUI

/// El plan del agente mientras trabaja — equivalente nativo de `PlanChecklist`
/// y `StepsPanel` de fi-glass. Sin esto, un turno que planifica y ejecuta pasos
/// se ve igual que uno colgado.
struct PlanChecklist: View {
    let plan: TurnPlan
    let herramientas: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            ForEach(Array(plan.pasos.enumerated()), id: \.offset) { _, paso in
                HStack(alignment: .top, spacing: 8) {
                    icono(paso.estado)
                        .font(.system(size: 12, weight: .semibold))
                        .frame(width: 16)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(paso.etiqueta)
                            .font(.footnote)
                            .foregroundStyle(color(paso.estado))
                        if let detalle = paso.detalle ?? paso.nota {
                            Text(detalle)
                                .font(.caption2)
                                .foregroundStyle(Theme.textFaint)
                        }
                    }
                }
            }
            if !herramientas.isEmpty {
                Text(herramientas.joined(separator: " · "))
                    .font(.caption2.monospaced())
                    .foregroundStyle(Theme.textFaint)
                    .padding(.top, 2)
            }
        }
        .padding(11)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.bubbleAssistant, in: RoundedRectangle(cornerRadius: 12))
        .overlay(
            RoundedRectangle(cornerRadius: 12).stroke(Theme.bubbleBorder, lineWidth: 1)
        )
    }

    @ViewBuilder
    private func icono(_ estado: TurnPlan.Paso.Estado) -> some View {
        switch estado {
        case .pendiente: Image(systemName: "circle").foregroundStyle(Theme.textFaint)
        case .corriendo: ProgressView().scaleEffect(0.5).tint(Theme.accent)
        case .hecho: Image(systemName: "checkmark.circle.fill").foregroundStyle(Theme.accent)
        case .fallido: Image(systemName: "xmark.circle.fill").foregroundStyle(Theme.danger)
        case .cancelado: Image(systemName: "minus.circle").foregroundStyle(Theme.textFaint)
        }
    }

    private func color(_ estado: TurnPlan.Paso.Estado) -> Color {
        switch estado {
        case .pendiente, .cancelado: Theme.textMuted
        case .corriendo, .hecho: Theme.textBody
        case .fallido: Theme.danger
        }
    }
}
