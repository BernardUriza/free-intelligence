import Foundation

/// El evento como lo consume ESTA app. El equivalente exacto de `mapEvent` en
/// `useOg118Agent.ts`: la forma del cable la declara el contrato y la genera el
/// codegen (`WireEvent.generated.swift`); aquí sólo se traduce a lo que la
/// pantalla necesita.
///
/// Antes este archivo era una transcripción a mano del contrato, y cada error
/// de transcripción shippeó.
enum StreamEvent {
    case open
    case text(String)
    case author(id: String, name: String)
    case toolCall(name: String, server: String?, isError: Bool)
    case result(text: String, model: String?)
    case done
    case failure(String)
    case plan([String])
    case stepStarted(Int)
    case stepDone(index: Int, status: StepStatus, summary: String?, error: String?)
    case stepNoted(index: Int, note: String)
    /// El ciclo de vida del plan. El diferenciador es "ver la ejecución, no sólo
    /// el resultado": un plan rechazado por el guard, reestructurado a media
    /// marcha o abandonado son cosas que el usuario TIENE que ver, y hasta ahora
    /// llegaban al teléfono como "frame sin mapear".
    case planRejected(razon: String, etiquetas: [String], guardia: String?)
    case planAmended(TurnPlan.Enmienda)
    case planCancelled
    case planClosed(TurnPlan.Desenlace)
    /// Un frame que el contrato declara pero esta pantalla todavía no usa, o uno
    /// que este build no conoce. Se muestra en la bitácora en vez de perderse.
    case unmapped(String)
}

enum StepStatus: String {
    case done
    case failed
    case cancelled
}

extension StreamEvent {
    static func decode(_ payload: Data) -> StreamEvent? {
        guard let wire = try? JSONDecoder().decode(WireEvent.self, from: payload) else { return nil }
        return map(wire)
    }

    static func map(_ wire: WireEvent) -> StreamEvent? {
        switch wire {
        case .open:
            return .open
        case .text(let texto):
            return .text(texto)
        case .element(let elemento):
            // `label` es el compuesto "53 · I · Yodo"; se prefiere el nombre.
            let nombre = elemento.name.flatMap { $0.isEmpty ? nil : $0 }
                ?? (elemento.label.isEmpty ? elemento.id : elemento.label)
            guard !elemento.id.isEmpty else { return nil }
            return .author(id: elemento.id, name: nombre)
        case .toolCall(let herramienta):
            return .toolCall(
                name: herramienta.name,
                server: herramienta.server,
                isError: herramienta.isError ?? false
            )
        case .result(let resultado):
            return .result(text: resultado.text ?? "", model: resultado.model)
        case .plan(let datos):
            return .plan(datos.steps)
        case .stepStarted(let datos):
            return .stepStarted(datos.stepIndex)
        case .stepDone(let datos):
            return .stepDone(
                index: datos.stepIndex,
                status: StepStatus(rawValue: datos.status.rawValue) ?? .done,
                summary: datos.summary,
                error: datos.error
            )
        case .stepNoted(let datos):
            return .stepNoted(index: datos.stepIndex, note: datos.note)
        case .error(let mensaje):
            return .failure(mensaje)
        case .done:
            return .done
        case .ping:
            // Señal de vida de un turno lento; no cambia nada en pantalla.
            return nil
        case .planRejected(let datos):
            return .planRejected(
                razon: datos.reason,
                etiquetas: (datos.matched ?? []).map(\.label),
                guardia: datos.`guard`
            )
        case .planAmended(let datos):
            return .planAmended(TurnPlan.Enmienda(rawValue: datos.action.rawValue) ?? .insertado)
        case .planCancelled:
            return .planCancelled
        case .planCompleted:
            return .planClosed(.completado)
        case .planFailed:
            return .planClosed(.fallido)
        case .desconocido(let tipo):
            return .unmapped(tipo)
        }
    }
}
