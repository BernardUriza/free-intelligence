import Foundation

/// El mensaje del hilo. Vive en Models y no dentro del cliente HTTP: para
/// entender la forma de un mensaje nadie debería tener que abrir networking.
/// `CodingKeys` deja fuera id/author/timestamp a propósito — el history que
/// viaja a /chat/stream es sólo role+content, como en el web.
struct ChatMessage: Identifiable, Encodable {
    enum Role: String, Encodable {
        case user
        case assistant
    }

    var id = UUID()
    let role: Role
    var content: String
    /// El autor canónico del contrato: `id` es load-bearing (la web lo necesita
    /// para atribuir la burbuja al elemento correcto), `nombre` es lo que se
    /// pinta. Guardar sólo el nombre dejaba records que la web no podía leer.
    struct Autor: Equatable {
        let id: String
        let nombre: String
    }

    var author: Autor?
    var timestamp: String?
    /// El modelo que produjo la respuesta: alimenta la píldora «Powered by» y
    /// viaja en `trace.model`, igual que lo persiste la web.
    var model: String?
    /// Las imágenes que el usuario adjuntó al turno. No viajan en `history`
    /// (CodingKeys): una imagen ya enviada no se re-sube en silencio.
    var images: [MessageImage] = []
    /// El gesto del que habló (emoji sobre el turno): un campo del contrato,
    /// nunca texto. Un mensaje puede ser SÓLO reacciones.
    var reactions: [String] = []

    enum CodingKeys: String, CodingKey {
        case role
        case content
    }
}

extension ChatMessage {
    /// Lo que una recarga muestra: el id no viaja al servidor, así que dos copias
    /// del mismo mensaje se reconocen por (role, timestamp, content).
    var claveDeHilo: String {
        "\(role.rawValue)\u{0}\(timestamp ?? "")\u{0}\(content)"
    }

    /// core `mergeConversationMessages`: todo `destino` más lo que sólo `fuente`
    /// tiene, ordenado por timestamp (estable en empates); nil si no agrega nada.
    static func unir(_ destino: [ChatMessage], _ fuente: [ChatMessage]) -> [ChatMessage]? {
        let conocidos = Set(destino.map(\.claveDeHilo))
        let faltan = fuente.filter { !conocidos.contains($0.claveDeHilo) }
        guard !faltan.isEmpty else { return nil }
        return (destino + faltan).enumerated()
            .sorted { a, b in
                let ta = a.element.timestamp ?? "", tb = b.element.timestamp ?? ""
                return ta != tb ? ta < tb : a.offset < b.offset
            }
            .map(\.element)
    }
}
