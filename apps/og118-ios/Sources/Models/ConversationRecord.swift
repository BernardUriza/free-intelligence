import Foundation

/// El autor del contrato canónico (`MessageAuthor` de free-intelligence-core):
/// un OBJETO `{id, name, symbol?, engine?}`, no un string. La app nativa lo
/// declaraba `String?` y por eso TODA conversación creada en la web reventaba al
/// decodificar —`«messages.Index 0.author» no es String`— y el hilo se veía
/// vacío en el teléfono.
///
/// Decodifica las dos formas porque el propio iOS ya escribió strings sueltos en
/// la cuenta; escribe SIEMPRE la canónica, para que la web pueda leer lo que el
/// teléfono guarda.
struct PersistedAuthor: Codable, Equatable {
    let id: String
    let name: String
    let symbol: String?
    let engine: String?

    init(id: String, name: String, symbol: String? = nil, engine: String? = nil) {
        self.id = id
        self.name = name
        self.symbol = symbol
        self.engine = engine
    }

    init(from decoder: Decoder) throws {
        if let suelto = try? decoder.singleValueContainer().decode(String.self) {
            // Legado del propio iOS: sólo teníamos el nombre.
            self.init(id: "", name: suelto)
            return
        }
        let c = try decoder.container(keyedBy: CodingKeys.self)
        self.init(
            id: try c.decodeIfPresent(String.self, forKey: .id) ?? "",
            name: try c.decodeIfPresent(String.self, forKey: .name) ?? "",
            symbol: try c.decodeIfPresent(String.self, forKey: .symbol),
            engine: try c.decodeIfPresent(String.self, forKey: .engine)
        )
    }
}

struct PersistedMessage: Codable {
    let role: String
    let content: String
    let timestamp: String?
    let author: PersistedAuthor?
}

struct ConversationSummary: Codable, Identifiable {
    let id: String
    let title: String
    let createdAt: String
    let updatedAt: String
    let preview: String?
    let pinnedAt: String?
    let archivedAt: String?

    var isArchived: Bool { archivedAt != nil }
    var isPinned: Bool { pinnedAt != nil }
}

struct ConversationList: Codable {
    let conversations: [ConversationSummary]
}

struct ConversationRecord: Codable {
    var id: String
    var title: String
    var titleCustom: Bool?
    var createdAt: String
    var updatedAt: String
    var messages: [PersistedMessage]
    var preview: String
    var pinnedAt: String?
    var archivedAt: String?
    var schemaVersion: Int
}

private let formatoISOFraccional: ISO8601DateFormatter = {
    let f = ISO8601DateFormatter()
    f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    return f
}()

private let formatoISOPlano: ISO8601DateFormatter = {
    let f = ISO8601DateFormatter()
    f.formatOptions = [.withInternetDateTime]
    return f
}()

enum ConversationSchema {
    static let version = 1

    /// Los timestamps del contrato llegan ISO-8601 con o sin fracciones de
    /// segundo según quién los escribió; los formatters viven fuera de la
    /// función porque construir un `ISO8601DateFormatter` por llamada es caro.
    static func fecha(_ iso: String) -> Date? {
        formatoISOFraccional.date(from: iso) ?? formatoISOPlano.date(from: iso)
    }
    static let defaultTitle = "New chat"
    static let titleMax = 60
    static let previewMax = 120

    static func truncate(_ text: String, _ max: Int) -> String {
        let collapsed = text
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .split(whereSeparator: { $0.isWhitespace })
            .joined(separator: " ")
        guard collapsed.count > max else { return collapsed }
        let cut = String(collapsed.prefix(Swift.max(0, max - 1)))
        return cut.replacingOccurrences(of: "\\s+$", with: "", options: .regularExpression) + "…"
    }

    static func title(_ messages: [ChatMessage]) -> String {
        let firstUser = messages.first {
            $0.role == .user && !$0.content.trimmingCharacters(in: .whitespaces).isEmpty
        }
        guard let firstUser else { return defaultTitle }
        let derived = truncate(firstUser.content, titleMax)
        return derived.isEmpty ? defaultTitle : derived
    }

    static func preview(_ messages: [ChatMessage]) -> String {
        for message in messages.reversed()
        where !message.content.trimmingCharacters(in: .whitespaces).isEmpty {
            return truncate(message.content, previewMax)
        }
        return ""
    }
}

extension ConversationRecord {
    /// `base` es el record tal como vive en el servidor. El PUT es reemplazo
    /// completo: sin arrastrar `titleCustom`/`pinnedAt`/`archivedAt`, un turno
    /// enviado desde el teléfono borraría el rename, el pin o el archivado que
    /// el usuario hizo en la web.
    static func from(
        id: String,
        messages: [ChatMessage],
        createdAt: String,
        now: String,
        base: ConversationRecord? = nil
    ) -> ConversationRecord {
        let customTitle = base?.titleCustom == true ? base?.title : nil
        return ConversationRecord(
            id: id,
            title: customTitle ?? ConversationSchema.title(messages),
            titleCustom: base?.titleCustom,
            createdAt: createdAt,
            updatedAt: now,
            messages: messages.map {
                PersistedMessage(
                    role: $0.role.rawValue,
                    content: $0.content,
                    timestamp: $0.timestamp,
                    author: $0.author.map {
                        PersistedAuthor(id: $0.id, name: $0.nombre)
                    }
                )
            },
            preview: ConversationSchema.preview(messages),
            pinnedAt: base?.pinnedAt,
            archivedAt: base?.archivedAt,
            schemaVersion: ConversationSchema.version
        )
    }

    var chatMessages: [ChatMessage] {
        messages.compactMap { persisted in
            guard let role = ChatMessage.Role(rawValue: persisted.role) else { return nil }
            return ChatMessage(
                role: role,
                content: persisted.content,
                author: persisted.author.map {
                    ChatMessage.Autor(id: $0.id, nombre: $0.name)
                },
                timestamp: persisted.timestamp
            )
        }
    }
}
