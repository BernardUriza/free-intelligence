import Foundation

/// La lista de conversaciones: los tres grupos del sidebar y las mutaciones
/// (fijar, archivar, renombrar, borrar).
///
/// Vivía dentro de ChatModel.swift por accidente histórico, no por cohesión:
/// no comparte con ChatModel ni un tipo ni un helper. Un archivo de 460 líneas
/// hospedando dos modelos independientes cuesta comprensión sin comprar nada.
@MainActor
final class ConversationsModel: ObservableObject {
    @Published private(set) var summaries: [ConversationSummary] = []
    @Published private(set) var isLoading = false
    @Published var errorMessage: String?

    typealias List = () async throws -> [ConversationSummary]
    typealias Load = (String) async throws -> ConversationRecord?
    typealias Save = (ConversationRecord) async throws -> Void
    typealias Remove = (String) async throws -> Void

    private let list: List
    private let load: Load?
    private let save: Save?
    private let remove: Remove?
    private let now: () -> String

    init(
        list: @escaping List,
        load: Load? = nil,
        save: Save? = nil,
        remove: Remove? = nil,
        now: @escaping () -> String = { ISO8601DateFormatter().string(from: Date()) }
    ) {
        self.list = list
        self.load = load
        self.save = save
        self.remove = remove
        self.now = now
    }

    convenience init(client: Og118Client) {
        self.init(
            list: client.listConversations,
            load: client.loadConversation,
            save: client.saveConversation,
            remove: client.deleteConversation
        )
    }

    /// Las tres vistas del sidebar web (`organizeConversationSummaries`):
    /// Fijados (último fijado primero), Chats (más reciente primero) y
    /// Archivados (último archivado primero).
    var pinned: [ConversationSummary] {
        summaries.filter { $0.isPinned && !$0.isArchived }
            .sorted { ($0.pinnedAt ?? "") > ($1.pinnedAt ?? "") }
    }

    var active: [ConversationSummary] {
        summaries.filter { !$0.isPinned && !$0.isArchived }
            .sorted { $0.updatedAt > $1.updatedAt }
    }

    var archived: [ConversationSummary] {
        summaries.filter { $0.isArchived }
            .sorted { ($0.archivedAt ?? "") > ($1.archivedAt ?? "") }
    }

    func refresh() async {
        guard !isLoading else { return }
        isLoading = true
        defer { isLoading = false }
        do {
            summaries = try await list()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @discardableResult
    func setPinned(_ id: String, _ pinned: Bool) async -> ConversationRecord? {
        await mutate(id) { $0.pinnedAt = pinned ? self.now() : nil }
    }

    @discardableResult
    func setArchived(_ id: String, _ archived: Bool) async -> ConversationRecord? {
        await mutate(id) { $0.archivedAt = archived ? self.now() : nil }
    }

    /// Renombrar con título vacío regresa al título auto-derivado, igual que
    /// la web (`onRename` con cadena vacía).
    @discardableResult
    func rename(_ id: String, to title: String) async -> ConversationRecord? {
        let limpio = ConversationSchema.truncate(title, ConversationSchema.titleMax)
        return await mutate(id) { record in
            if limpio.isEmpty {
                record.title = ConversationSchema.title(record.chatMessages)
                record.titleCustom = nil
            } else {
                record.title = limpio
                record.titleCustom = true
            }
        }
    }

    func delete(_ id: String) async {
        guard let remove else { return }
        do {
            try await remove(id)
            summaries.removeAll { $0.id == id }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    /// Carga el record completo, lo transforma y lo re-sube: el servidor sólo
    /// habla PUT de reemplazo completo, así que la mutación mínima es
    /// load → editar campo → save.
    private func mutate(
        _ id: String,
        _ transform: (inout ConversationRecord) -> Void
    ) async -> ConversationRecord? {
        guard let load, let save else { return nil }
        do {
            guard var record = try await load(id) else { return nil }
            transform(&record)
            record.updatedAt = now()
            try await save(record)
            await reload()
            return record
        } catch {
            errorMessage = error.localizedDescription
            return nil
        }
    }

    private func reload() async {
        do {
            summaries = try await list()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
