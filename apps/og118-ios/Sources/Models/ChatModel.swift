import Foundation

@MainActor
final class ChatModel: ObservableObject {
    @Published private(set) var messages: [ChatMessage] = []
    @Published private(set) var liveText = ""
    @Published private(set) var liveAuthor: ChatMessage.Autor?
    private var liveModel: String?
    @Published private(set) var plan = TurnPlan()
    /// El texto del turno que se puede volver a intentar. Existe porque un turno
    /// que muere no debe obligar a reteclear: el mensaje ya está en el hilo.
    @Published private(set) var reintentable: String?
    @Published private(set) var herramientas: [String] = []
    @Published private(set) var isStreaming = false
    @Published private(set) var isRestoring = false
    /// El hilo acepta turnos sólo cuando ya se sabe qué hay en el servidor:
    /// escribir sobre un restore fallido reemplazaba la conversación entera.
    @Published private(set) var hiloListo: Bool
    @Published private(set) var cargaFallida: String?
    @Published var errorMessage: String?

    typealias Stream = (
        _ message: String,
        _ sessionID: String,
        _ history: [ChatMessage],
        _ corpusID: String?,
        _ element: String?,
        _ images: [MessageImage]
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
    private var esperabaRecord = false

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
        self.hiloListo = restore == nil
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
        guard let restore else {
            hiloListo = true
            return
        }
        guard !isRestoring, !hiloListo else { return }
        self.esperabaRecord = esperabaRecord
        isRestoring = true
        cargaFallida = nil
        defer { isRestoring = false }
        do {
            guard let record = try await restore(conversationID) else {
                if esperabaRecord {
                    cargaFallida = "Esta conversación no está en tu cuenta."
                } else {
                    hiloListo = true
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
            hiloListo = true
        } catch {
            cargaFallida = error.localizedDescription
        }
    }

    func reintentarCarga() {
        Task { await restoreThread(esperabaRecord: esperabaRecord) }
    }

    func open(_ id: String) async {
        if id == conversationID {
            if !hiloListo { await restoreThread(esperabaRecord: true) }
            return
        }
        cancel()
        conversationID = id
        ConversationIdentity.set(id, defaults: defaults)
        reiniciarHilo()
        hiloListo = false
        await restoreThread(esperabaRecord: true)
    }

    func startNew() {
        cancel()
        conversationID = ConversationIdentity.fresh(defaults: defaults)
        reiniciarHilo()
        hiloListo = true
    }

    private func reiniciarHilo() {
        messages = []
        liveText = ""
        liveAuthor = nil
        liveModel = nil
        errorMessage = nil
        cargaFallida = nil
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

    /// Un envío de sólo imagen es válido —la foto ES el mensaje—, como en la web.
    func send(_ text: String, images: [MessageImage] = []) {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard hiloListo, !trimmed.isEmpty || !images.isEmpty, !isStreaming else { return }

        let history = messages
        messages.append(ChatMessage(role: .user, content: trimmed, timestamp: now(), images: images))
        lanzarTurno(trimmed, images: images, history: history)
    }

    /// Repite el turno muerto. El mensaje del usuario YA está en el hilo, así
    /// que reintentar no vuelve a agregarlo: sólo rehace la parte que falló.
    func reintentar() {
        guard let texto = reintentable, !isStreaming else { return }
        let imagenes = messages.last(where: { $0.role == .user })?.images ?? []
        lanzarTurno(texto, images: imagenes, history: Array(messages.dropLast()))
    }

    private func lanzarTurno(_ texto: String, images: [MessageImage], history: [ChatMessage]) {
        liveText = ""
        liveAuthor = nil
        liveModel = nil
        plan = TurnPlan()
        herramientas = []
        errorMessage = nil
        reintentable = nil
        framesDelTurno = 0
        isStreaming = true

        turn = Task {
            do {
                for try await event in stream(texto, conversationID, history, corpusID, element, images) {
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
        liveModel = nil
    }

    private func apply(_ event: StreamEvent) {
        guard isStreaming else { return }
        framesDelTurno += 1
        switch event {
        case .text(let delta):
            liveText += delta
        case .author(let id, let name):
            liveAuthor = ChatMessage.Autor(id: id, nombre: name)
        case .result(let text, let model):
            if !text.isEmpty { liveText = text }
            if let model, !model.isEmpty { liveModel = model }
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
                    timestamp: now(),
                    model: liveModel
                )
            )
        }
        liveText = ""
        liveAuthor = nil
        liveModel = nil
        save()
    }

    /// Los guardados van encadenados: dos PUT concurrentes al mismo id se
    /// resuelven last-write-wins en el servidor, así que un snapshot viejo que
    /// llegue tarde borraría el turno más reciente.
    private func save() {
        guard let persist, hiloListo, !messages.isEmpty else { return }
        let locales = messages
        let base = baseRecord
        let id = conversationID
        let creado = createdAt
        let previous = saveChain
        saveChain = Task { [weak self] in
            await previous?.value
            guard let self else { return }
            let vivo = await self.releer(id)
            let record = ConversationRecord.fusionar(
                id: id, locales: locales, base: base, vivo: vivo, createdAt: creado, now: self.now()
            )
            self.adoptarFusion(record, locales: locales)
            do {
                try await persist(record)
            } catch {
                self.errorMessage = error.localizedDescription
            }
        }
    }

    /// El PUT es reemplazo total y otro escritor (la web, el drawer) pudo
    /// cambiar el hilo mientras tanto: se relee antes de escribir.
    private func releer(_ id: String) async -> ConversationRecord? {
        guard let restore else { return nil }
        return try? await restore(id)
    }

    private func adoptarFusion(_ record: ConversationRecord, locales: [ChatMessage]) {
        guard record.id == conversationID else { return }
        baseRecord = record
        if record.messages.count > locales.count, messages.map(\.id) == locales.map(\.id) {
            messages = record.chatMessages
        }
    }
}
