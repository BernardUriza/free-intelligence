import Foundation

@MainActor
final class ChatModel: ObservableObject {
    @Published private(set) var messages: [ChatMessage] = []
    @Published private(set) var liveText = ""
    @Published private(set) var liveAuthor: ChatMessage.Autor?
    @Published private(set) var plan = TurnPlan()
    /// El texto del turno que se puede volver a intentar. Existe porque un turno
    /// que muere no debe obligar a reteclear: el mensaje ya está en el hilo.
    @Published private(set) var reintentable: String?
    @Published private(set) var herramientas: [String] = []
    @Published private(set) var isStreaming = false
    @Published private(set) var isRestoring = false
    @Published var errorMessage: String?

    typealias Stream = (
        _ message: String,
        _ sessionID: String,
        _ history: [ChatMessage],
        _ corpusID: String?,
        _ element: String?
    ) -> AsyncThrowingStream<StreamEvent, Error>
    typealias Persist = (ConversationRecord) async throws -> Void
    typealias Restore = (String) async throws -> ConversationRecord?

    @Published private(set) var conversationID: String

    /// Elemento activo (token que el registry resuelve) y proyecto activo
    /// (su id ES el corpus_id). Ausentes = companion base sin corpus, que es
    /// exactamente lo que el servidor entiende por omitir los campos.
    @Published var element: String? {
        didSet { TurnContextStore.saveElement(element, defaults: defaults) }
    }
    @Published var corpusID: String? {
        didSet { TurnContextStore.saveCorpus(corpusID, defaults: defaults) }
    }

    private let stream: Stream
    private let persist: Persist?
    private let restore: Restore?
    private let now: () -> String
    private let defaults: UserDefaults
    private var createdAt: String
    /// El record tal como llegó del servidor: al persistir se arrastran sus
    /// campos de metadata (titleCustom, pinnedAt, archivedAt) porque el PUT es
    /// reemplazo completo.
    private var baseRecord: ConversationRecord?
    private var turn: Task<Void, Never>?
    private var saveChain: Task<Void, Never>?
    private var framesDelTurno = 0

    init(
        conversationID: String = ConversationIdentity.current(),
        stream: @escaping Stream,
        persist: Persist? = nil,
        restore: Restore? = nil,
        now: @escaping () -> String = { ISO8601DateFormatter().string(from: Date()) },
        defaults: UserDefaults = .standard
    ) {
        self.conversationID = conversationID
        self.defaults = defaults
        self.element = TurnContextStore.loadElement(defaults: defaults)
        self.corpusID = TurnContextStore.loadCorpus(defaults: defaults)
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

    /// `esperabaRecord` distingue arrancar en una conversación NUEVA (donde no
    /// haber record es lo normal) de abrir una que el usuario acaba de tocar en
    /// la lista (donde no haber record es una falla). Sin esa distinción, un
    /// chat que no carga se ve idéntico a uno vacío — el mismo silencio que ya
    /// nos costó horas con la lista.
    func restoreThread(esperabaRecord: Bool = false) async {
        guard let restore, messages.isEmpty, !isRestoring else { return }
        isRestoring = true
        defer { isRestoring = false }
        do {
            guard let record = try await restore(conversationID) else {
                if esperabaRecord {
                    errorMessage = "Esta conversación no está en tu cuenta."
                }
                return
            }
            createdAt = record.createdAt
            baseRecord = record
            messages = record.chatMessages
            // Un record con mensajes que se quedan en cero significa que el
            // cliente no supo leer su forma: hay que gritarlo, no mostrar un
            // hilo vacío como si la conversación no tuviera nada.
            if messages.isEmpty, !record.messages.isEmpty {
                errorMessage = "Llegaron \(record.messages.count) mensajes que esta versión no supo leer."
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func open(_ id: String) async {
        guard id != conversationID else { return }
        cancel()
        conversationID = id
        ConversationIdentity.set(id, defaults: defaults)
        messages = []
        liveText = ""
        liveAuthor = nil
        errorMessage = nil
        // Sin esto, un turno fallido en el chat A dejaba su texto en
        // `reintentable`; al abrir B y toparse con CUALQUIER error, el botón
        // Reintentar reaparecía y mandaba el mensaje de A dentro de B.
        reintentable = nil
        plan = TurnPlan()
        herramientas = []
        createdAt = now()
        baseRecord = nil
        await restoreThread(esperabaRecord: true)
    }

    func startNew() {
        cancel()
        conversationID = ConversationIdentity.fresh(defaults: defaults)
        messages = []
        liveText = ""
        liveAuthor = nil
        errorMessage = nil
        // Sin esto, un turno fallido en el chat A dejaba su texto en
        // `reintentable`; al abrir B y toparse con CUALQUIER error, el botón
        // Reintentar reaparecía y mandaba el mensaje de A dentro de B.
        reintentable = nil
        plan = TurnPlan()
        herramientas = []
        createdAt = now()
        baseRecord = nil
    }

    /// Una mutación externa (pin, rename, archivar) reemplazó el record en el
    /// servidor. Si es la conversación abierta, el próximo save debe partir de
    /// esa versión — partir del snapshot viejo desharía la mutación.
    func adoptBase(_ record: ConversationRecord) {
        guard record.id == conversationID else { return }
        baseRecord = record
    }

    func send(_ text: String) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !isStreaming else { return }

        let history = messages
        messages.append(ChatMessage(role: .user, content: trimmed, timestamp: now()))
        lanzarTurno(trimmed, history: history)
    }

    /// Repite el turno muerto. El mensaje del usuario YA está en el hilo, así
    /// que reintentar no vuelve a agregarlo: sólo rehace la parte que falló.
    func reintentar() {
        guard let texto = reintentable, !isStreaming else { return }
        lanzarTurno(texto, history: Array(messages.dropLast()))
    }

    private func lanzarTurno(_ texto: String, history: [ChatMessage]) {
        liveText = ""
        liveAuthor = nil
        plan = TurnPlan()
        herramientas = []
        errorMessage = nil
        reintentable = nil
        framesDelTurno = 0
        isStreaming = true

        turn = Task {
            do {
                for try await event in stream(texto, conversationID, history, corpusID, element) {
                    apply(event)
                }
            } catch is CancellationError {
            } catch {
                errorMessage = error.localizedDescription
            }
            fold(texto)
        }
    }

    func cancel() {
        turn?.cancel()
        turn = nil
        discardLiveTurn()
    }

    /// Un turno cancelado NO deja respuesta. Persistir el texto a medias lo
    /// devolvería como `history` en el turno siguiente y el modelo leería su
    /// propia frase mutilada como contexto.
    private func discardLiveTurn() {
        guard isStreaming else { return }
        isStreaming = false
        liveText = ""
        liveAuthor = nil
    }

    private func apply(_ event: StreamEvent) {
        guard isStreaming else { return }
        framesDelTurno += 1
        switch event {
        case .text(let delta):
            liveText += delta
        case .author(let id, let name):
            liveAuthor = ChatMessage.Autor(id: id, nombre: name)
        case .result(let text, _):
            if !text.isEmpty { liveText = text }
        case .failure(let message):
            errorMessage = message
        case .plan(let etiquetas):
            plan.declarar(etiquetas)
        case .stepStarted(let i):
            plan.empezar(i)
        case .stepDone(let i, let estado, let resumen, let error):
            plan.cerrar(i, estado: estado, resumen: resumen, error: error)
        case .stepNoted(let i, let nota):
            plan.anotar(i, nota: nota)
        case .planRejected(let razon, let etiquetas, let guardia):
            plan.rechazar(TurnPlan.Rechazo(razon: razon, etiquetas: etiquetas, guardia: guardia))
        case .planAmended(let accion):
            plan.enmendar(accion)
        case .planCancelled:
            plan.cancelar()
        case .planClosed(let desenlace):
            plan.cerrarPlan(desenlace)
        case .toolCall(let nombre, let servidor, let esError):
            let etiqueta = servidor.map { "\($0)/\(nombre)" } ?? nombre
            herramientas.append(esError ? "\(etiqueta) ✗" : etiqueta)
        case .unmapped(let tipo):
            // Antes esto era `break`: un frame desconocido desaparecía sin
            // rastro. Ahora al menos queda en la bitácora del turno.
            herramientas.append("frame sin mapear: \(tipo)")
        case .open, .done:
            break
        }
    }

    private func fold(_ enviado: String) {
        guard isStreaming else { return }
        isStreaming = false

        // Un turno que cierra sin una sola palabra se veía EXACTAMENTE igual
        // que uno pensando: silencio. Ahora se declara, y con el conteo de
        // frames, que es lo que separa "el servidor no contestó" de "contestó
        // puros frames que no traían texto".
        if liveText.isEmpty, errorMessage == nil {
            errorMessage = framesDelTurno == 0
                ? "El servidor cerró el turno sin mandar un solo frame."
                : "Llegaron \(framesDelTurno) frames pero ninguno traía texto."
        }
        if errorMessage != nil { reintentable = enviado }

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

    /// Los guardados van encadenados: dos PUT concurrentes al mismo id se
    /// resuelven last-write-wins en el servidor, así que un snapshot viejo que
    /// llegue tarde borraría el turno más reciente.
    private func save() {
        guard let persist, !messages.isEmpty else { return }
        let record = ConversationRecord.from(
            id: conversationID,
            messages: messages,
            createdAt: createdAt,
            now: now(),
            base: baseRecord
        )
        baseRecord = record
        let previous = saveChain
        saveChain = Task { [weak self] in
            await previous?.value
            do {
                try await persist(record)
            } catch {
                await MainActor.run { self?.errorMessage = error.localizedDescription }
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
