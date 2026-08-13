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

    enum CodingKeys: String, CodingKey {
        case role
        case content
    }
}
