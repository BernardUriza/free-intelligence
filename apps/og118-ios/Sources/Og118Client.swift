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

    enum CodingKeys: String, CodingKey {
        case message
        case history
        case sessionID = "session_id"
    }
}

struct Og118Client {
    var accessToken: () async throws -> String

    func stream(
        message: String,
        sessionID: String,
        history: [ChatMessage]
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
                        ChatRequest(message: message, sessionID: sessionID, history: history)
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

    private func emit(
        _ payload: String,
        to continuation: AsyncThrowingStream<StreamEvent, Error>.Continuation
    ) {
        guard !payload.isEmpty, let data = payload.data(using: .utf8) else { return }
        guard let event = StreamEvent.decode(data) else { return }
        continuation.yield(event)
    }
}
