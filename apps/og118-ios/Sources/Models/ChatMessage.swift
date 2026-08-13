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
    var author: String?
    var timestamp: String?

    enum CodingKeys: String, CodingKey {
        case role
        case content
    }
}
