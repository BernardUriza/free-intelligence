import Foundation

@MainActor
final class ChatModel: ObservableObject {
    @Published private(set) var messages: [ChatMessage] = []
    @Published private(set) var liveText = ""
    @Published private(set) var liveAuthor: String?
    @Published private(set) var isStreaming = false
    @Published private(set) var isRestoring = false
    @Published var errorMessage: String?

    typealias Stream = (
        _ message: String,
        _ sessionID: String,
        _ history: [ChatMessage]
    ) -> AsyncThrowingStream<StreamEvent, Error>
    typealias Persist = (ConversationRecord) async throws -> Void
    typealias Restore = (String) async throws -> ConversationRecord?

    @Published private(set) var conversationID: String

    private let stream: Stream
    private let persist: Persist?
    private let restore: Restore?
    private let now: () -> String
    private var createdAt: String
    private var turn: Task<Void, Never>?

    init(
        conversationID: String = ConversationIdentity.current(),
        stream: @escaping Stream,
        persist: Persist? = nil,
        restore: Restore? = nil,
        now: @escaping () -> String = { ISO8601DateFormatter().string(from: Date()) }
    ) {
        self.conversationID = conversationID
        self.stream = stream
        self.persist = persist
        self.restore = restore
        self.now = now
        self.createdAt = now()
    }

    convenience init(client: Og118Client) {
        self.init(
            stream: client.stream,
            persist: client.saveConversation,
            restore: client.loadConversation
        )
    }

    func restoreThread() async {
        guard let restore, messages.isEmpty, !isRestoring else { return }
        isRestoring = true
        defer { isRestoring = false }
        do {
            guard let record = try await restore(conversationID) else { return }
            createdAt = record.createdAt
            messages = record.chatMessages
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func open(_ id: String) async {
        guard id != conversationID else { return }
        cancel()
        conversationID = id
        ConversationIdentity.set(id)
        messages = []
        liveText = ""
        liveAuthor = nil
        errorMessage = nil
        createdAt = now()
        await restoreThread()
    }

    func startNew() {
        cancel()
        conversationID = ConversationIdentity.fresh()
        messages = []
        liveText = ""
        liveAuthor = nil
        errorMessage = nil
        createdAt = now()
    }

    func send(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !isStreaming else { return }

        let history = messages
        messages.append(ChatMessage(role: .user, content: trimmed, timestamp: now()))
        liveText = ""
        liveAuthor = nil
        errorMessage = nil
        isStreaming = true

        turn = Task {
            do {
                for try await event in stream(trimmed, conversationID, history) {
                    apply(event)
                }
            } catch is CancellationError {
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
            messages.append(
                ChatMessage(
                    role: .assistant,
                    content: liveText,
                    author: liveAuthor,
                    timestamp: now()
                )
            )
        }
        liveText = ""
        liveAuthor = nil
        save()
    }

    private func save() {
        guard let persist, !messages.isEmpty else { return }
        let record = ConversationRecord.from(
            id: conversationID,
            messages: messages,
            createdAt: createdAt,
            now: now()
        )
        Task {
            do {
                try await persist(record)
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }
}

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

@MainActor
final class ConversationsModel: ObservableObject {
    @Published private(set) var summaries: [ConversationSummary] = []
    @Published private(set) var isLoading = false
    @Published var errorMessage: String?

    typealias List = () async throws -> [ConversationSummary]

    private let list: List

    init(list: @escaping List) {
        self.list = list
    }

    convenience init(client: Og118Client) {
        self.init(list: client.listConversations)
    }

    func refresh() async {
        guard !isLoading else { return }
        isLoading = true
        defer { isLoading = false }
        do {
            summaries = try await list().filter { !$0.isArchived }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
