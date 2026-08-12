import Foundation

@MainActor
final class ChatModel: ObservableObject {
    @Published private(set) var messages: [ChatMessage] = []
    @Published private(set) var liveText = ""
    @Published private(set) var author: String?
    @Published private(set) var isStreaming = false
    @Published var errorMessage: String?

    private let sessionID = UUID().uuidString
    private let client: Og118Client
    private var turn: Task<Void, Never>?

    init(client: Og118Client) {
        self.client = client
    }

    func send(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !isStreaming else { return }

        let history = messages
        messages.append(ChatMessage(role: .user, content: trimmed))
        liveText = ""
        author = nil
        errorMessage = nil
        isStreaming = true

        turn = Task {
            do {
                for try await event in client.stream(
                    message: trimmed,
                    sessionID: sessionID,
                    history: history
                ) {
                    apply(event)
                }
            } catch {
                errorMessage = error.localizedDescription
            }
            fold()
        }
    }

    func cancel() {
        turn?.cancel()
        turn = nil
        fold()
    }

    private func apply(_ event: StreamEvent) {
        switch event {
        case .text(let delta):
            liveText += delta
        case .author(_, let name):
            author = name
        case .result(let text, _):
            if !text.isEmpty { liveText = text }
        case .failure(let message):
            errorMessage = message
        case .open, .done, .toolCall, .unmapped:
            break
        }
    }

    private func fold() {
        if !liveText.isEmpty {
            messages.append(ChatMessage(role: .assistant, content: liveText))
        }
        liveText = ""
        isStreaming = false
    }
}
