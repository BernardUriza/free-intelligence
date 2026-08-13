import Foundation

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

enum Og118Error: LocalizedError {
    case unauthorized
    case badStatus(Int)
    case notHTTP

    var errorDescription: String? {
        switch self {
        case .unauthorized:
            return "Tu sesión expiró. Inicia sesión otra vez."
        case .badStatus(let code):
            return "El servidor respondió \(code)."
        case .notHTTP:
            return "Respuesta no reconocida del servidor."
        }
    }
}

private struct ChatRequest: Encodable {
    let message: String
    let sessionID: String
    let history: [ChatMessage]
    let corpusID: String?
    let element: String?

    enum CodingKeys: String, CodingKey {
        case message
        case history
        case element
        case sessionID = "session_id"
        case corpusID = "corpus_id"
    }
}

struct Og118Client {
    var accessToken: () async throws -> String

    func stream(
        message: String,
        sessionID: String,
        history: [ChatMessage],
        corpusID: String?,
        element: String?
    ) -> AsyncThrowingStream<StreamEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    var request = URLRequest(url: Config.apiBase.appendingPathComponent("chat/stream"))
                    request.httpMethod = "POST"
                    request.timeoutInterval = 300
                    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                    request.setValue("text/event-stream", forHTTPHeaderField: "Accept")

                    let token = try await accessToken()
                    if !token.isEmpty {
                        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
                    }

                    request.httpBody = try JSONEncoder().encode(
                        ChatRequest(
                            message: message,
                            sessionID: sessionID,
                            history: history,
                            corpusID: corpusID,
                            element: element
                        )
                    )

                    let (bytes, response) = try await URLSession.shared.bytes(for: request)
                    guard let http = response as? HTTPURLResponse else { throw Og118Error.notHTTP }
                    if http.statusCode == 401 { throw Og118Error.unauthorized }
                    guard (200..<300).contains(http.statusCode) else {
                        throw Og118Error.badStatus(http.statusCode)
                    }

                    var payload = ""
                    for try await line in bytes.lines {
                        if line.isEmpty {
                            emit(payload, to: continuation)
                            payload = ""
                        } else if line.hasPrefix("data:") {
                            payload += line.dropFirst(5).trimmingCharacters(in: .whitespaces)
                        }
                    }
                    emit(payload, to: continuation)
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    func listElements() async throws -> [Element] {
        try await get("elements", as: ElementList.self).elements
    }

    func listProjects() async throws -> [Project] {
        try await get("projects", as: ProjectList.self).projects
    }

    private func get<T: Decodable>(_ path: String, as type: T.Type) async throws -> T {
        var request = URLRequest(url: Config.apiBase.appendingPathComponent(path))
        try await authorize(&request)
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw Og118Error.notHTTP }
        if http.statusCode == 401 { throw Og118Error.unauthorized }
        guard (200..<300).contains(http.statusCode) else {
            throw Og118Error.badStatus(http.statusCode)
        }
        return try JSONDecoder().decode(T.self, from: data)
    }

    func listConversations() async throws -> [ConversationSummary] {
        var request = URLRequest(url: Config.apiBase.appendingPathComponent("conversations"))
        try await authorize(&request)
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw Og118Error.notHTTP }
        if http.statusCode == 401 { throw Og118Error.unauthorized }
        guard (200..<300).contains(http.statusCode) else {
            throw Og118Error.badStatus(http.statusCode)
        }
        return try JSONDecoder().decode(ConversationList.self, from: data).conversations
    }

    func loadConversation(id: String) async throws -> ConversationRecord? {
        var request = URLRequest(url: Config.apiBase.appendingPathComponent("conversations/\(id)"))
        try await authorize(&request)
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw Og118Error.notHTTP }
        if http.statusCode == 404 { return nil }
        if http.statusCode == 401 { throw Og118Error.unauthorized }
        guard (200..<300).contains(http.statusCode) else {
            throw Og118Error.badStatus(http.statusCode)
        }
        return try JSONDecoder().decode(ConversationRecord.self, from: data)
    }

    func saveConversation(_ record: ConversationRecord) async throws {
        var request = URLRequest(
            url: Config.apiBase.appendingPathComponent("conversations/\(record.id)")
        )
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        try await authorize(&request)
        request.httpBody = try JSONEncoder().encode(record)

        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw Og118Error.notHTTP }
        if http.statusCode == 401 { throw Og118Error.unauthorized }
        guard (200..<300).contains(http.statusCode) else {
            throw Og118Error.badStatus(http.statusCode)
        }
    }

    func deleteConversation(id: String) async throws {
        var request = URLRequest(
            url: Config.apiBase.appendingPathComponent("conversations/\(id)")
        )
        request.httpMethod = "DELETE"
        try await authorize(&request)
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw Og118Error.notHTTP }
        if http.statusCode == 401 { throw Og118Error.unauthorized }
        guard (200..<300).contains(http.statusCode) else {
            throw Og118Error.badStatus(http.statusCode)
        }
    }

    private func authorize(_ request: inout URLRequest) async throws {
        let token = try await accessToken()
        if !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
    }

    private func emit(
        _ payload: String,
        to continuation: AsyncThrowingStream<StreamEvent, Error>.Continuation
    ) {
        guard !payload.isEmpty, let data = payload.data(using: .utf8) else { return }
        guard let event = StreamEvent.decode(data) else { return }
        continuation.yield(event)
    }
}
