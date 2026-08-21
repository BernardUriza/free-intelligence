import Foundation

/// El servidor de og118 corre con `minReplicas: 0`, así que tras un rato sin
/// uso Azure lo apaga y la PRIMERA petición sólo sirve para despertarlo: se
/// queda esperando el arranque del contenedor y muchas veces muere antes de
/// que el proceso exista. En el teléfono eso se veía como "Cargando tus
/// chats…" para siempre — el log del servidor mostraba el arranque a la misma
/// hora de la captura y CERO peticiones después.
///
/// La cura es asumir que la primera petición puede ser el despertador: se le
/// pone un plazo corto y se reintenta contra el servidor ya despierto.
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
