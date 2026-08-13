import Foundation

/// El troceador de SSE, separado del transporte para poder probarlo con bytes
/// REALES capturados del servidor. Mientras vivió dentro del `for await` de
/// URLSession no había forma de demostrar que leía bien un turno de verdad.
///
/// El contrato del servidor (`_sse` en app.py) es `data: {json}\n\n`: las líneas
/// `data:` se concatenan y la línea en blanco cierra el frame.
struct SSEParser {
    private var payload = ""

    /// Alimenta una línea. Devuelve el frame si esa línea lo cerró.
    mutating func feed(_ line: String) -> StreamEvent? {
        if line.isEmpty {
            return cerrar()
        }
        if line.hasPrefix("data:") {
            payload += line.dropFirst(5).trimmingCharacters(in: .whitespaces)
        }
        return nil
    }

    /// El último frame cuando el stream termina sin línea en blanco final.
    mutating func cerrar() -> StreamEvent? {
        defer { payload = "" }
        guard !payload.isEmpty, let data = payload.data(using: .utf8) else { return nil }
        return StreamEvent.decode(data)
    }
}
