import Foundation

/// Bitácora del turno visible en la app. La falla del chat no se reproduce
/// desde la Mac —el servidor responde bien— así que el diagnóstico tiene que
/// vivir donde ocurre: en el teléfono.
@MainActor
final class TurnDiagnostics: ObservableObject {
    @Published private(set) var lineas: [String] = []

    func limpiar() { lineas = [] }

    func anotar(_ texto: String) {
        lineas.append(texto)
        if lineas.count > 12 { lineas.removeFirst() }
    }

    var resumen: String? { lineas.isEmpty ? nil : lineas.joined(separator: "\n") }
}
