import Foundation

struct PersistedMessage: Codable {
    let role: String
    let content: String
    let timestamp: String?
    let author: String?
}

struct ConversationRecord: Codable {
    let id: String
    let title: String
    let titleCustom: Bool?
    let createdAt: String
    let updatedAt: String
    let messages: [PersistedMessage]
    let preview: String
    let schemaVersion: Int
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
    static func from(
        id: String,
        messages: [ChatMessage],
        createdAt: String,
        now: String
    ) -> ConversationRecord {
        ConversationRecord(
            id: id,
            title: ConversationSchema.title(messages),
            titleCustom: nil,
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
