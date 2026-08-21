import Foundation

/// El plan glass-box del agente durante un turno. Existe porque el servidor lo
/// emite y la app lo estaba tirando: sin esto, un turno que planifica y ejecuta
/// pasos se ve idéntico a uno colgado.
struct TurnPlan: Equatable {
    struct Paso: Equatable {
        var etiqueta: String
        var estado: Estado = .pendiente
        var nota: String?
        var detalle: String?

        enum Estado: Equatable {
            case pendiente
            case corriendo
            case hecho
            case fallido
            case cancelado
        }
    }

    var pasos: [Paso] = []

    var vacio: Bool { pasos.isEmpty }

    mutating func declarar(_ etiquetas: [String]) {
        pasos = etiquetas.map { Paso(etiqueta: $0) }
    }

    mutating func empezar(_ indice: Int) {
        guard pasos.indices.contains(indice) else { return }
        pasos[indice].estado = .corriendo
    }

    mutating func cerrar(_ indice: Int, estado: StepStatus, resumen: String?, error: String?) {
        guard pasos.indices.contains(indice) else { return }
        pasos[indice].estado = switch estado {
        case .done: .hecho
        case .failed: .fallido
        case .cancelled: .cancelado
        }
        pasos[indice].detalle = error ?? resumen
    }

    mutating func anotar(_ indice: Int, nota: String) {
        guard pasos.indices.contains(indice) else { return }
        pasos[indice].nota = nota
    }
}
