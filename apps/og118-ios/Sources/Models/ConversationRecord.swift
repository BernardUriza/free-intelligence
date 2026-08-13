import Foundation

/// Las formas (`ConversationRecord`, `PersistedMessage`, `MessageAuthor`,
/// `MessageImage`, `MessageTrace`) viven en `Generated/ConversationRecord.generated.swift`,
/// derivadas del contrato. Este archivo sólo tiene COMPORTAMIENTO: la tolerancia
/// al formato viejo, las derivaciones de título/preview y el armado del record.

/// El iOS ya escribió `author` como string suelto en la cuenta de Bernard antes
/// de conocer el contrato. Normalizar el JSON ANTES de decodificar deja esos
/// records legibles sin ensuciar el tipo generado con un caso que el contrato
/// no declara — la deuda vive en el borde, no en la forma.
enum LegadoDeAutor {
    static func normalizar(_ datos: Data) -> Data {
        guard var raiz = try? JSONSerialization.jsonObject(with: datos) as? [String: Any],
              var mensajes = raiz["messages"] as? [[String: Any]] else { return datos }
        var cambio = false
        for i in mensajes.indices {
            if let nombre = mensajes[i]["author"] as? String {
                mensajes[i]["author"] = ["id": "", "name": nombre]
                cambio = true
            }
        }
        guard cambio else { return datos }
        raiz["messages"] = mensajes
        return (try? JSONSerialization.data(withJSONObject: raiz)) ?? datos
    }
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
    /// Un turno sólo AGREGA mensajes: los primeros N del hilo son, uno a uno,
    /// los que ya venían en el record. Así que se re-escriben VERBATIM —con sus
    /// imágenes, su trace y todo lo que esta versión no entiende— y sólo los
    /// nuevos se construyen desde el modelo del teléfono.
    private static func preservando(
        _ messages: [ChatMessage],
        base: ConversationRecord?
    ) -> [PersistedMessage] {
        let previos = base?.messages ?? []
        return messages.enumerated().map { indice, mensaje in
            if indice < previos.count { return previos[indice] }
            return PersistedMessage(
                role: PersistedMessageRole(rawValue: mensaje.role.rawValue) ?? .user,
                content: mensaje.content,
                timestamp: mensaje.timestamp,
                author: mensaje.author.map { MessageAuthor(id: $0.id, name: $0.nombre) }
            )
        }
    }

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
            messages: preservando(messages, base: base),
            preview: ConversationSchema.preview(messages),
            pinnedAt: base?.pinnedAt,
            archivedAt: base?.archivedAt,
            schemaVersion: ConversationSchema.version
        )
    }

    var chatMessages: [ChatMessage] {
        messages.compactMap { persisted in
            // El contrato ya restringe el rol a user|assistant, así que el
            // enum generado no puede traer otra cosa: el descarte silencioso
            // que había aquí dejó de ser posible.
            guard let role = ChatMessage.Role(rawValue: persisted.role.rawValue) else { return nil }
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
