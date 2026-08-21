import Foundation
import os

/// Bitácora del turno. Vive en dos lados a propósito: en la pantalla, para que
/// Bernard vea qué pasó sin cablear nada; y en el log unificado, para que la
/// misma línea se pueda leer desde la Mac con
/// `devicectl device process launch --console`, sin pedirle que transcriba.
@MainActor
final class TurnDiagnostics: ObservableObject {
    @Published private(set) var lineas: [String] = []

    private let bitacora = Logger(subsystem: "com.bernard.og118", category: "turno")

    func limpiar() { lineas = [] }

    func anotar(_ texto: String) {
        // .public porque el log unificado redacta las interpolaciones por
        // defecto y una bitácora de <private> no diagnostica nada.
        bitacora.notice("\(texto, privacy: .public)")
        // stdout es lo que `devicectl --console` entrega a la Mac; el Logger
        // solo, sin consola atachada, se queda dentro del teléfono.
        print("[turno] \(texto)")
        lineas.append(texto)
        if lineas.count > 12 { lineas.removeFirst() }
    }

    var resumen: String? { lineas.isEmpty ? nil : lineas.joined(separator: "\n") }
}
