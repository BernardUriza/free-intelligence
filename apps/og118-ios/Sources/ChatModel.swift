import Foundation

@MainActor
final class ChatModel: ObservableObject {
    @Published private(set) var messages: [ChatMessage] = []
    @Published private(set) var liveText = ""
    @Published private(set) var liveAuthor: String?
    @Published private(set) var isStreaming = false
    @Published var errorMessage: String?

    typealias Stream = (
        _ message: String,
        _ sessionID: String,
        _ history: [ChatMessage]
    ) -> AsyncThrowingStream<StreamEvent, Error>

    private let sessionID = UUID().uuidString
    private let stream: Stream
    private var turn: Task<Void, Never>?

    init(stream: @escaping Stream) {
        self.stream = stream
    }

    convenience init(client: Og118Client) {
        self.init(stream: client.stream)
    }

    func send(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !isStreaming else { return }

        let history = messages
        messages.append(ChatMessage(role: .user, content: trimmed))
        liveText = ""
        liveAuthor = nil
        errorMessage = nil
        isStreaming = true

        turn = Task {
            do {
                for try await event in stream(trimmed, sessionID, history) {
                    apply(event)
                }
            } catch is CancellationError {
                // el fold ya lo hizo cancel()
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
        guard isStreaming else { return }
        switch event {
        case .text(let delta):
            liveText += delta
        case .author(_, let name):
            liveAuthor = name
        case .result(let text, _):
            if !text.isEmpty { liveText = text }
        case .failure(let message):
            errorMessage = message
        case .open, .done, .toolCall, .unmapped:
            break
        }
    }

    private func fold() {
        guard isStreaming else { return }
        isStreaming = false
        if !liveText.isEmpty {
            messages.append(ChatMessage(role: .assistant, content: liveText, author: liveAuthor))
        }
        liveText = ""
        liveAuthor = nil
    }
}
