import Foundation

/// La primera petición tras un despliegue o un reinicio del contenedor puede
/// morir antes de que el proceso exista: se le pone un plazo corto y se repite.
enum ArranqueEnFrio {
    /// Plazo de la primera petición. Corto a propósito: si el servidor está
    /// dormido no vale la pena esperar el timeout largo del sistema, y si está
    /// despierto responde en menos de un segundo.
    static let plazoDespertador: TimeInterval = 20

    /// Corre `operacion`, y si falla por plazo/conexión la repite UNA vez.
    /// Un fallo que no sea de red (401, 404, JSON inválido) no se reintenta:
    /// repetirlo daría el mismo error y sólo retrasaría el mensaje al humano.
    static func conReintento<T>(
        _ operacion: (_ esReintento: Bool) async throws -> T
    ) async throws -> T {
        do {
            return try await operacion(false)
        } catch {
            guard esDeRed(error) else { throw error }
            return try await operacion(true)
        }
    }

    static func esDeRed(_ error: Error) -> Bool {
        let url = error as? URLError
        guard let codigo = url?.code else { return false }
        return [
            .timedOut,
            .cannotConnectToHost,
            .networkConnectionLost,
            .notConnectedToInternet,
            .dnsLookupFailed
        ].contains(codigo)
    }
}
