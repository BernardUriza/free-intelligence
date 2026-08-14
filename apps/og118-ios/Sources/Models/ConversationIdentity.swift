import Foundation

/// Qué conversación está abierta, persistido entre arranques. Pequeño pero
/// load-bearing: es lo que hace que la app reabra donde la dejaste, y lo que
/// garantiza que el `session_id` que viaja al servidor sea el id de la
/// conversación y no uno aleatorio.
enum ConversationIdentity {
    private static let key = "og118.conversation.id"

    static func current(defaults: UserDefaults = .standard) -> String {
        if let existing = defaults.string(forKey: key), !existing.isEmpty {
            return existing
        }
        return fresh(defaults: defaults)
    }

    static func set(_ id: String, defaults: UserDefaults = .standard) {
        defaults.set(id, forKey: key)
    }

    @discardableResult
    static func fresh(defaults: UserDefaults = .standard) -> String {
        let id = UUID().uuidString
        defaults.set(id, forKey: key)
        return id
    }
}
