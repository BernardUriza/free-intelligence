// DO NOT EDIT — generado desde contracts/conversation-record.schema.json
//
// El schema es LA FUENTE, escrita a mano. TypeScript, Swift y el modelo del
// servidor derivan de él; ninguno manda sobre los otros. Un contrato que vive
// como tipos de UN lenguaje obliga a los demás a transcribirlo, y cada
// transcripción diverge — así se perdieron las imágenes y así se vaciaron los
// hilos de la web en el teléfono.
//
//   pnpm --filter @free-intelligence/core gen:swift-record
//   pnpm --filter @free-intelligence/core check:swift-record

import Foundation

enum PersistedMessageRole: String, Codable {
    case user = "user"
    case assistant = "assistant"
}

enum AgentPlanOutcome: String, Codable {
    case completed = "completed"
    case failed = "failed"
    case cancelled = "cancelled"
}

enum PlanStepStatus: String, Codable {
    case pending = "pending"
    case running = "running"
    case done = "done"
    case failed = "failed"
    case cancelled = "cancelled"
}

/// Un mensaje TAL COMO SE GUARDA. No es el ChatMessage vivo: `sanitizeConversationMessage` descarta `metadata`, `id` y `thinking` a propósito, así que este contrato tampoco los declara. Lo que sí sobrevive —autoría, imágenes, trace— sobrevive porque es contenido que el usuario vería desaparecer.
struct PersistedMessage: Codable {
    /// De qué lado del hilo está el mensaje.
    var role: PersistedMessageRole
    /// El texto. Puede ir vacío en un mensaje que sólo lleva imagen.
    var content: String
    /// ISO 8601.
    var timestamp: String?
    var author: MessageAuthor?
    var images: [MessageImage]?
    var trace: MessageTrace?

    init(role: PersistedMessageRole, content: String, timestamp: String? = nil, author: MessageAuthor? = nil, images: [MessageImage]? = nil, trace: MessageTrace? = nil) {
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.author = author
        self.images = images
        self.trace = trace
    }

    /// Campos que este build no conoce todavía. Viajan intactos.
    var ajenos: [String: JSONValor] = [:]

    private static let propias: Set<String> = ["role", "content", "timestamp", "author", "images", "trace"]

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: LlaveLibre.self)
        role = try c.decode(PersistedMessageRole.self, forKey: LlaveLibre(stringValue: "role"))
        content = try c.decode(String.self, forKey: LlaveLibre(stringValue: "content"))
        timestamp = try c.decodeIfPresent(String.self, forKey: LlaveLibre(stringValue: "timestamp"))
        author = try c.decodeIfPresent(MessageAuthor.self, forKey: LlaveLibre(stringValue: "author"))
        images = try c.decodeIfPresent([MessageImage].self, forKey: LlaveLibre(stringValue: "images"))
        trace = try c.decodeIfPresent(MessageTrace.self, forKey: LlaveLibre(stringValue: "trace"))
        var resto: [String: JSONValor] = [:]
        for llave in c.allKeys where !Self.propias.contains(llave.stringValue) {
            resto[llave.stringValue] = try c.decode(JSONValor.self, forKey: llave)
        }
        ajenos = resto
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LlaveLibre.self)
        try c.encode(role, forKey: LlaveLibre(stringValue: "role"))
        try c.encode(content, forKey: LlaveLibre(stringValue: "content"))
        try c.encodeIfPresent(timestamp, forKey: LlaveLibre(stringValue: "timestamp"))
        try c.encodeIfPresent(author, forKey: LlaveLibre(stringValue: "author"))
        try c.encodeIfPresent(images, forKey: LlaveLibre(stringValue: "images"))
        try c.encodeIfPresent(trace, forKey: LlaveLibre(stringValue: "trace"))
        for (llave, valor) in ajenos {
            try c.encode(valor, forKey: LlaveLibre(stringValue: llave))
        }
    }
}

/// QUIÉN habló — el hablante nombrado, no sólo el lado. Una burbuja de asistente sin autor atribuye la respuesta a la app misma, y eso es una mentira que el framework no debe poder expresar. Sólo `id` y `name` son load-bearing.
struct MessageAuthor: Codable {
    /// Identificador estable del hablante (id de elemento, de persona, 'user').
    var id: String
    /// Nombre humano que se pinta ('Yodo', 'og118', 'Tú').
    var name: String
    /// Enriquecimiento opcional: token de avatar.
    var symbol: String?
    /// Enriquecimiento opcional: chip de procedencia.
    var engine: String?

    init(id: String, name: String, symbol: String? = nil, engine: String? = nil) {
        self.id = id
        self.name = name
        self.symbol = symbol
        self.engine = engine
    }

    /// Campos que este build no conoce todavía. Viajan intactos.
    var ajenos: [String: JSONValor] = [:]

    private static let propias: Set<String> = ["id", "name", "symbol", "engine"]

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: LlaveLibre.self)
        id = try c.decode(String.self, forKey: LlaveLibre(stringValue: "id"))
        name = try c.decode(String.self, forKey: LlaveLibre(stringValue: "name"))
        symbol = try c.decodeIfPresent(String.self, forKey: LlaveLibre(stringValue: "symbol"))
        engine = try c.decodeIfPresent(String.self, forKey: LlaveLibre(stringValue: "engine"))
        var resto: [String: JSONValor] = [:]
        for llave in c.allKeys where !Self.propias.contains(llave.stringValue) {
            resto[llave.stringValue] = try c.decode(JSONValor.self, forKey: llave)
        }
        ajenos = resto
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LlaveLibre.self)
        try c.encode(id, forKey: LlaveLibre(stringValue: "id"))
        try c.encode(name, forKey: LlaveLibre(stringValue: "name"))
        try c.encodeIfPresent(symbol, forKey: LlaveLibre(stringValue: "symbol"))
        try c.encodeIfPresent(engine, forKey: LlaveLibre(stringValue: "engine"))
        for (llave, valor) in ajenos {
            try c.encode(valor, forKey: LlaveLibre(stringValue: llave))
        }
    }
}

/// Una imagen adjunta a un mensaje del usuario. Base64 por diseño: los shells son local-first, así que los bytes viajan dentro del mensaje en vez de referenciar un blob store que nadie corre.
struct MessageImage: Codable {
    /// MIME de los bytes, p. ej. image/jpeg.
    var mediaType: String
    /// Bytes en base64 — SIN el prefijo data: URL.
    var data: String

    init(mediaType: String, data: String) {
        self.mediaType = mediaType
        self.data = data
    }

    /// Campos que este build no conoce todavía. Viajan intactos.
    var ajenos: [String: JSONValor] = [:]

    private static let propias: Set<String> = ["mediaType", "data"]

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: LlaveLibre.self)
        mediaType = try c.decode(String.self, forKey: LlaveLibre(stringValue: "mediaType"))
        data = try c.decode(String.self, forKey: LlaveLibre(stringValue: "data"))
        var resto: [String: JSONValor] = [:]
        for llave in c.allKeys where !Self.propias.contains(llave.stringValue) {
            resto[llave.stringValue] = try c.decode(JSONValor.self, forKey: llave)
        }
        ajenos = resto
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LlaveLibre.self)
        try c.encode(mediaType, forKey: LlaveLibre(stringValue: "mediaType"))
        try c.encode(data, forKey: LlaveLibre(stringValue: "data"))
        for (llave, valor) in ajenos {
            try c.encode(valor, forKey: LlaveLibre(stringValue: llave))
        }
    }
}

/// La foto glass-box del turno agéntico ya terminado. El diferenciador es 'ver la ejecución, no sólo el resultado': sin esto, recargar una conversación pierde el plan y las herramientas que el turno vivo sí mostró. Todo es opcional — un turno conversacional simple dobla sin trace.
struct MessageTrace: Codable {
    var plan: AgentPlan?
    var tools: [ToolCall]?
    var sources: [String]?
    /// El modelo que DE VERDAD produjo la respuesta. Vive aquí y no en metadata, que la persistencia descarta por diseño.
    var model: String?

    init(plan: AgentPlan? = nil, tools: [ToolCall]? = nil, sources: [String]? = nil, model: String? = nil) {
        self.plan = plan
        self.tools = tools
        self.sources = sources
        self.model = model
    }

    /// Campos que este build no conoce todavía. Viajan intactos.
    var ajenos: [String: JSONValor] = [:]

    private static let propias: Set<String> = ["plan", "tools", "sources", "model"]

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: LlaveLibre.self)
        plan = try c.decodeIfPresent(AgentPlan.self, forKey: LlaveLibre(stringValue: "plan"))
        tools = try c.decodeIfPresent([ToolCall].self, forKey: LlaveLibre(stringValue: "tools"))
        sources = try c.decodeIfPresent([String].self, forKey: LlaveLibre(stringValue: "sources"))
        model = try c.decodeIfPresent(String.self, forKey: LlaveLibre(stringValue: "model"))
        var resto: [String: JSONValor] = [:]
        for llave in c.allKeys where !Self.propias.contains(llave.stringValue) {
            resto[llave.stringValue] = try c.decode(JSONValor.self, forKey: llave)
        }
        ajenos = resto
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LlaveLibre.self)
        try c.encodeIfPresent(plan, forKey: LlaveLibre(stringValue: "plan"))
        try c.encodeIfPresent(tools, forKey: LlaveLibre(stringValue: "tools"))
        try c.encodeIfPresent(sources, forKey: LlaveLibre(stringValue: "sources"))
        try c.encodeIfPresent(model, forKey: LlaveLibre(stringValue: "model"))
        for (llave, valor) in ajenos {
            try c.encode(valor, forKey: LlaveLibre(stringValue: llave))
        }
    }
}

struct AgentPlan: Codable {
    var steps: [PlanStep]
    /// Veredicto terminal del plan completo.
    var outcome: AgentPlanOutcome?

    init(steps: [PlanStep], outcome: AgentPlanOutcome? = nil) {
        self.steps = steps
        self.outcome = outcome
    }

    /// Campos que este build no conoce todavía. Viajan intactos.
    var ajenos: [String: JSONValor] = [:]

    private static let propias: Set<String> = ["steps", "outcome"]

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: LlaveLibre.self)
        steps = try c.decode([PlanStep].self, forKey: LlaveLibre(stringValue: "steps"))
        outcome = try c.decodeIfPresent(AgentPlanOutcome.self, forKey: LlaveLibre(stringValue: "outcome"))
        var resto: [String: JSONValor] = [:]
        for llave in c.allKeys where !Self.propias.contains(llave.stringValue) {
            resto[llave.stringValue] = try c.decode(JSONValor.self, forKey: llave)
        }
        ajenos = resto
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LlaveLibre.self)
        try c.encode(steps, forKey: LlaveLibre(stringValue: "steps"))
        try c.encodeIfPresent(outcome, forKey: LlaveLibre(stringValue: "outcome"))
        for (llave, valor) in ajenos {
            try c.encode(valor, forKey: LlaveLibre(stringValue: llave))
        }
    }
}

struct PlanStep: Codable {
    var label: String
    var status: PlanStepStatus
    var summary: String?
    var error: String?
    /// Anotación libre de note_step.
    var note: String?

    init(label: String, status: PlanStepStatus, summary: String? = nil, error: String? = nil, note: String? = nil) {
        self.label = label
        self.status = status
        self.summary = summary
        self.error = error
        self.note = note
    }

    /// Campos que este build no conoce todavía. Viajan intactos.
    var ajenos: [String: JSONValor] = [:]

    private static let propias: Set<String> = ["label", "status", "summary", "error", "note"]

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: LlaveLibre.self)
        label = try c.decode(String.self, forKey: LlaveLibre(stringValue: "label"))
        status = try c.decode(PlanStepStatus.self, forKey: LlaveLibre(stringValue: "status"))
        summary = try c.decodeIfPresent(String.self, forKey: LlaveLibre(stringValue: "summary"))
        error = try c.decodeIfPresent(String.self, forKey: LlaveLibre(stringValue: "error"))
        note = try c.decodeIfPresent(String.self, forKey: LlaveLibre(stringValue: "note"))
        var resto: [String: JSONValor] = [:]
        for llave in c.allKeys where !Self.propias.contains(llave.stringValue) {
            resto[llave.stringValue] = try c.decode(JSONValor.self, forKey: llave)
        }
        ajenos = resto
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LlaveLibre.self)
        try c.encode(label, forKey: LlaveLibre(stringValue: "label"))
        try c.encode(status, forKey: LlaveLibre(stringValue: "status"))
        try c.encodeIfPresent(summary, forKey: LlaveLibre(stringValue: "summary"))
        try c.encodeIfPresent(error, forKey: LlaveLibre(stringValue: "error"))
        try c.encodeIfPresent(note, forKey: LlaveLibre(stringValue: "note"))
        for (llave, valor) in ajenos {
            try c.encode(valor, forKey: LlaveLibre(stringValue: llave))
        }
    }
}

struct ToolCall: Codable {
    /// Id estable del proveedor; ausente mientras está pendiente.
    var id: String?
    /// Identificador de la herramienta como la nombró el agente.
    var name: String
    /// Servidor/namespace de origen; ausente en las builtin.
    var server: String?
    /// Ausente = pendiente, false = ok, true = falló.
    var isError: Bool?

    init(id: String? = nil, name: String, server: String? = nil, isError: Bool? = nil) {
        self.id = id
        self.name = name
        self.server = server
        self.isError = isError
    }

    /// Campos que este build no conoce todavía. Viajan intactos.
    var ajenos: [String: JSONValor] = [:]

    private static let propias: Set<String> = ["id", "name", "server", "isError"]

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: LlaveLibre.self)
        id = try c.decodeIfPresent(String.self, forKey: LlaveLibre(stringValue: "id"))
        name = try c.decode(String.self, forKey: LlaveLibre(stringValue: "name"))
        server = try c.decodeIfPresent(String.self, forKey: LlaveLibre(stringValue: "server"))
        isError = try c.decodeIfPresent(Bool.self, forKey: LlaveLibre(stringValue: "isError"))
        var resto: [String: JSONValor] = [:]
        for llave in c.allKeys where !Self.propias.contains(llave.stringValue) {
            resto[llave.stringValue] = try c.decode(JSONValor.self, forKey: llave)
        }
        ajenos = resto
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LlaveLibre.self)
        try c.encodeIfPresent(id, forKey: LlaveLibre(stringValue: "id"))
        try c.encode(name, forKey: LlaveLibre(stringValue: "name"))
        try c.encodeIfPresent(server, forKey: LlaveLibre(stringValue: "server"))
        try c.encodeIfPresent(isError, forKey: LlaveLibre(stringValue: "isError"))
        for (llave, valor) in ajenos {
            try c.encode(valor, forKey: LlaveLibre(stringValue: llave))
        }
    }
}

/// El registro persistido de una conversación. ESTE ARCHIVO ES LA FUENTE: TypeScript, Swift y el modelo del servidor se derivan de aquí, ninguno manda sobre los otros. Escrito a mano a propósito — un contrato que vive como tipos de UN lenguaje obliga a los demás consumers a transcribirlo, y cada transcripción diverge: tipar `author` como string en vez del objeto canónico dejó toda conversación de la web vacía en el iPhone, y no modelar `images` hizo que guardar desde el teléfono las borrara.
struct ConversationRecord: Codable {
    /// Id estable. Es también el session_id del hilo en el backend.
    var id: String
    /// Derivado del primer mensaje del usuario, salvo que titleCustom sea true.
    var title: String
    /// True cuando el usuario renombró. Un título custom NUNCA se re-deriva al persistir.
    var titleCustom: Bool?
    /// ISO 8601.
    var createdAt: String
    /// ISO 8601 del último cambio.
    var updatedAt: String
    var messages: [PersistedMessage]
    /// Fragmento del último mensaje no vacío, para el sidebar.
    var preview: String
    /// ISO 8601. Ausente = no fijado. Timestamp y no booleano para que la sección ordene por último-fijado sin un contador aparte.
    var pinnedAt: String?
    /// ISO 8601. Ausente = activo.
    var archivedAt: String?
    /// Versión del registro, para migraciones hacia adelante.
    var schemaVersion: Int

    init(id: String, title: String, titleCustom: Bool? = nil, createdAt: String, updatedAt: String, messages: [PersistedMessage], preview: String, pinnedAt: String? = nil, archivedAt: String? = nil, schemaVersion: Int) {
        self.id = id
        self.title = title
        self.titleCustom = titleCustom
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.messages = messages
        self.preview = preview
        self.pinnedAt = pinnedAt
        self.archivedAt = archivedAt
        self.schemaVersion = schemaVersion
    }

    /// Campos que este build no conoce todavía. Viajan intactos.
    var ajenos: [String: JSONValor] = [:]

    private static let propias: Set<String> = ["id", "title", "titleCustom", "createdAt", "updatedAt", "messages", "preview", "pinnedAt", "archivedAt", "schemaVersion"]

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: LlaveLibre.self)
        id = try c.decode(String.self, forKey: LlaveLibre(stringValue: "id"))
        title = try c.decode(String.self, forKey: LlaveLibre(stringValue: "title"))
        titleCustom = try c.decodeIfPresent(Bool.self, forKey: LlaveLibre(stringValue: "titleCustom"))
        createdAt = try c.decode(String.self, forKey: LlaveLibre(stringValue: "createdAt"))
        updatedAt = try c.decode(String.self, forKey: LlaveLibre(stringValue: "updatedAt"))
        messages = try c.decode([PersistedMessage].self, forKey: LlaveLibre(stringValue: "messages"))
        preview = try c.decode(String.self, forKey: LlaveLibre(stringValue: "preview"))
        pinnedAt = try c.decodeIfPresent(String.self, forKey: LlaveLibre(stringValue: "pinnedAt"))
        archivedAt = try c.decodeIfPresent(String.self, forKey: LlaveLibre(stringValue: "archivedAt"))
        schemaVersion = try c.decode(Int.self, forKey: LlaveLibre(stringValue: "schemaVersion"))
        var resto: [String: JSONValor] = [:]
        for llave in c.allKeys where !Self.propias.contains(llave.stringValue) {
            resto[llave.stringValue] = try c.decode(JSONValor.self, forKey: llave)
        }
        ajenos = resto
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: LlaveLibre.self)
        try c.encode(id, forKey: LlaveLibre(stringValue: "id"))
        try c.encode(title, forKey: LlaveLibre(stringValue: "title"))
        try c.encodeIfPresent(titleCustom, forKey: LlaveLibre(stringValue: "titleCustom"))
        try c.encode(createdAt, forKey: LlaveLibre(stringValue: "createdAt"))
        try c.encode(updatedAt, forKey: LlaveLibre(stringValue: "updatedAt"))
        try c.encode(messages, forKey: LlaveLibre(stringValue: "messages"))
        try c.encode(preview, forKey: LlaveLibre(stringValue: "preview"))
        try c.encodeIfPresent(pinnedAt, forKey: LlaveLibre(stringValue: "pinnedAt"))
        try c.encodeIfPresent(archivedAt, forKey: LlaveLibre(stringValue: "archivedAt"))
        try c.encode(schemaVersion, forKey: LlaveLibre(stringValue: "schemaVersion"))
        for (llave, valor) in ajenos {
            try c.encode(valor, forKey: LlaveLibre(stringValue: llave))
        }
    }
}
