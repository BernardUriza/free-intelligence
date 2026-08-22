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

    /// El guard bloqueó el plan. "Guard-as-quality": el rechazo es parte del
    /// plan, no un error aparte — el stream sigue y el usuario debe VERLO.
    var rechazo: Rechazo?
    /// El agente reestructuró el plan a media marcha (`plan_amended`).
    var enmienda: Enmienda?
    /// Veredicto terminal del plan completo.
    var desenlace: Desenlace?

    struct Rechazo: Equatable {
        var razon: String
        var etiquetas: [String]
        var guardia: String?
    }

    enum Enmienda: String, Equatable {
        case insertado = "insert"
        case replanteado = "replan"
    }

    enum Desenlace: String, Equatable {
        case completado
        case fallido
        case cancelado
    }

    var vacio: Bool { pasos.isEmpty }

    mutating func declarar(_ etiquetas: [String]) {
        pasos = etiquetas.map { Paso(etiqueta: $0) }
        // Un plan nuevo limpia la enmienda: el replan ANUNCIA y luego declara
        // los pasos, así que la insignia sólo vive entre esos dos frames.
        enmienda = nil
        desenlace = nil
    }

    mutating func rechazar(_ rechazo: Rechazo) {
        self.rechazo = rechazo
    }

    mutating func enmendar(_ accion: Enmienda) {
        // El canónico sólo la registra si YA hay plan: una enmienda sin plan
        // que enmendar no significa nada.
        guard !pasos.isEmpty || rechazo != nil else { return }
        enmienda = accion
    }

    /// El plan entero se abandonó. Los pasos que seguían abiertos quedan
    /// CANCELADOS, no hechos — distinguirlos es lo que hace honesto al
    /// glass-box. Los ya terminados conservan su estado.
    mutating func cancelar() {
        for i in pasos.indices where pasos[i].estado == .pendiente || pasos[i].estado == .corriendo {
            pasos[i].estado = .cancelado
        }
        desenlace = .cancelado
    }

    mutating func cerrarPlan(_ desenlace: Desenlace) {
        guard !pasos.isEmpty else { return }
        self.desenlace = desenlace
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
