import Foundation

struct PersistedMessage: Codable {
    let role: String
    let content: String
    let timestamp: String?
    let author: String?
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

enum ConversationSchema {
    static let version = 1
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
                    author: $0.author
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
                author: persisted.author,
                timestamp: persisted.timestamp
            )
        }
    }
}
