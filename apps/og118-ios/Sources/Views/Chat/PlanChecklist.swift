import SwiftUI

/// El plan del agente mientras trabaja — equivalente nativo de `PlanChecklist`
/// y `StepsPanel` de fi-glass. Sin esto, un turno que planifica y ejecuta pasos
/// se ve igual que uno colgado.
struct PlanChecklist: View {
    let plan: TurnPlan
    let herramientas: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            if let rechazo = plan.rechazo {
                // El guard bloqueó el plan y el stream SIGUE: si esto no se
                // pinta, el usuario ve pasos corriendo sin saber que su plan
                // fue objetado.
                VStack(alignment: .leading, spacing: 3) {
                    Label(rechazo.razon, systemImage: "exclamationmark.shield")
                        .font(.footnote.weight(.medium))
                        .foregroundStyle(Theme.danger)
                    if !rechazo.etiquetas.isEmpty {
                        Text(rechazo.etiquetas.joined(separator: " · "))
                            .font(.caption2)
                            .foregroundStyle(Theme.textFaint)
                    }
                }
                .padding(.bottom, 2)
            }
            if let enmienda = plan.enmienda {
                Text(enmienda == .replanteado ? "El agente replanteó" : "El agente insertó pasos")
                    .font(.caption2.weight(.medium))
                    .foregroundStyle(Theme.textMuted)
            }
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
            if let desenlace = plan.desenlace {
                Text(textoDesenlace(desenlace))
                    .font(.caption2.weight(.medium))
                    .foregroundStyle(desenlace == .completado ? Theme.accent : Theme.textMuted)
                    .padding(.top, 2)
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

    private func textoDesenlace(_ d: TurnPlan.Desenlace) -> String {
        switch d {
        case .completado: "Plan completado"
        case .fallido: "El plan falló"
        case .cancelado: "Plan cancelado"
        }
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
