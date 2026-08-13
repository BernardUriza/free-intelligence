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
    ///
    /// El separador de SSE es la línea en blanco, pero `URLSession.AsyncBytes.lines`
    /// SE LAS TRAGA: un turno de 4 frames llegaba como 4 líneas, sin separador
    /// alguno, así que el parser nunca cerraba un frame y la app se quedaba
    /// muda con el texto ya en la mano. Por eso una línea `data:` nueva también
    /// cierra el frame anterior — pero sólo si lo que hay acumulado ya es JSON
    /// válido, de modo que un frame partido en varias líneas `data:` (que el
    /// spec permite) se sigue reensamblando.
    mutating func feed(_ line: String) -> StreamEvent? {
        if line.isEmpty {
            return cerrar()
        }
        guard line.hasPrefix("data:") else { return nil }
        let anterior = payload.isEmpty ? nil : cerrarSiEsJSONCompleto()
        payload += line.dropFirst(5).trimmingCharacters(in: .whitespaces)
        return anterior
    }

    private mutating func cerrarSiEsJSONCompleto() -> StreamEvent? {
        guard let data = payload.data(using: .utf8),
              (try? JSONSerialization.jsonObject(with: data)) != nil else { return nil }
        defer { payload = "" }
        return StreamEvent.decode(data)
    }

    /// El último frame cuando el stream termina sin línea en blanco final.
    mutating func cerrar() -> StreamEvent? {
        defer { payload = "" }
        guard !payload.isEmpty, let data = payload.data(using: .utf8) else { return nil }
        return StreamEvent.decode(data)
    }
}
