import Foundation

enum Og118Error: LocalizedError {
    case unauthorized
    case badStatus(Int)
    case notHTTP
    case formato(String)

    var errorDescription: String? {
        switch self {
        case .formato(let detalle):
            return "El servidor mandó algo que no supe leer: \(detalle)"
        case .unauthorized:
            return "Tu sesión expiró. Inicia sesión otra vez."
        case .badStatus(let code):
            return "El servidor respondió \(code)."
        case .notHTTP:
            return "Respuesta no reconocida del servidor."
        }
    }
}

struct ChatRequest: Encodable {
    let message: String
    let sessionID: String
    let history: [ChatMessage]
    let corpusID: String?
    let element: String?
    let images: [ImagenDelTurno]?

    enum CodingKeys: String, CodingKey {
        case message
        case history
        case element
        case images
        case sessionID = "session_id"
        case corpusID = "corpus_id"
    }
}

/// El `ChatImage` del servidor: en el cable es `media_type`, no el `mediaType` del record.
struct ImagenDelTurno: Encodable {
    let mediaType: String
    let data: String

    enum CodingKeys: String, CodingKey {
        case data
        case mediaType = "media_type"
    }
}

struct Og118Client {
    static func detalle(_ error: DecodingError) -> String {
        switch error {
        case .keyNotFound(let llave, let ctx):
            return "falta la llave «\(llave.stringValue)» en \(ruta(ctx))"
        case .typeMismatch(let tipo, let ctx):
            return "«\(ruta(ctx))» no es \(tipo)"
        case .valueNotFound(let tipo, let ctx):
            return "«\(ruta(ctx))» vino nulo y se esperaba \(tipo)"
        case .dataCorrupted(let ctx):
            return "dato corrupto en \(ruta(ctx)): \(ctx.debugDescription)"
        @unknown default:
            return "error de formato desconocido"
        }
    }

    private static func ruta(_ ctx: DecodingError.Context) -> String {
        let camino = ctx.codingPath.map(\.stringValue).filter { !$0.isEmpty }
        return camino.isEmpty ? "la raíz" : camino.joined(separator: ".")
    }

    var transporte: Transporte
    var diagnostico: TurnDiagnostics?

    private func anotar(_ texto: String) async {
        guard let diagnostico else { return }
        await MainActor.run { diagnostico.anotar(texto) }
    }

    func stream(
        message: String,
        sessionID: String,
        history: [ChatMessage],
        corpusID: String?,
        element: String?,
        images: [MessageImage] = []
    ) -> AsyncThrowingStream<StreamEvent, Error> {
        AsyncThrowingStream { continuation in
            let task = Task {
                do {
                    var request = URLRequest(url: Config.apiBase.appendingPathComponent("chat/stream"))
                    request.httpMethod = "POST"
                    request.timeoutInterval = 300
                    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                    request.setValue("text/event-stream", forHTTPHeaderField: "Accept")
                    request.httpBody = try JSONEncoder().encode(
                        ChatRequest(
                            message: message,
                            sessionID: sessionID,
                            history: history,
                            corpusID: corpusID,
                            element: element,
                            images: images.isEmpty
                                ? nil
                                : images.map { ImagenDelTurno(mediaType: $0.mediaType, data: $0.data) }
                        )
                    )

                    let bytes = try await abrirStream(request)
                    var parser = SSEParser()
                    var lineasVistas = 0
                    var framesEmitidos = 0
                    for try await line in bytes.lines {
                        lineasVistas += 1
                        if lineasVistas <= 2 {
                            await anotar("línea \(lineasVistas): \(line.prefix(60))")
                        }
                        if let evento = parser.feed(line) {
                            framesEmitidos += 1
                            continuation.yield(evento)
                        }
                    }
                    if let ultimo = parser.cerrar() {
                        framesEmitidos += 1
                        continuation.yield(ultimo)
                    }
                    await anotar("fin: \(lineasVistas) líneas, \(framesEmitidos) frames")
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    }

    /// El 401 llega con los encabezados, antes del primer frame: repetir el POST
    /// con un token nuevo no duplica ningún turno.
    private func abrirStream(_ request: URLRequest) async throws -> URLSession.AsyncBytes {
        var rechazado: String?
        while true {
            await anotar(rechazado == nil ? "pidiendo token…" : "401: refrescando token…")
            let (firmada, token) = try await transporte.autorizada(request, rechazado: rechazado)
            await anotar("POST \(Config.apiBase.host ?? "?")/chat/stream")
            let (bytes, response) = try await URLSession.shared.bytes(for: firmada)
            guard let http = response as? HTTPURLResponse else { throw Og118Error.notHTTP }
            await anotar("HTTP \(http.statusCode) · \(http.value(forHTTPHeaderField: "Content-Type") ?? "sin tipo")")
            if http.statusCode == 401 {
                if rechazado == nil {
                    rechazado = token
                    continue
                }
                await transporte.sesionRechazada()
                throw Og118Error.unauthorized
            }
            guard (200..<300).contains(http.statusCode) else {
                throw Og118Error.badStatus(http.statusCode)
            }
            return bytes
        }
    }

    private func pedir(_ request: URLRequest) async throws -> Data {
        let (data, http) = try await transporte.enviar(request, despertador: true)
        guard (200..<300).contains(http.statusCode) else {
            throw Og118Error.badStatus(http.statusCode)
        }
        return data
    }

    private func ruta(_ path: String, metodo: String = "GET") -> URLRequest {
        var request = URLRequest(url: Config.apiBase.appendingPathComponent(path))
        request.httpMethod = metodo
        return request
    }

    func listElements() async throws -> [Element] {
        try JSONDecoder().decode(ElementList.self, from: try await pedir(ruta("elements"))).elements
    }

    /// Con Proyectos apagado el servidor no monta la ruta y contesta 404: eso
    /// es «no hay proyectos», no una falla que haya que enseñarle a nadie.
    func listProjects() async throws -> [Project] {
        do {
            return try JSONDecoder().decode(ProjectList.self, from: try await pedir(ruta("projects"))).projects
        } catch Og118Error.badStatus(404) {
            return []
        }
    }

    func listConversations() async throws -> [ConversationSummary] {
        try JSONDecoder().decode(ConversationList.self, from: try await pedir(ruta("conversations"))).conversations
    }

    func loadConversation(id: String) async throws -> ConversationRecord? {
        let data: Data
        do {
            data = try await pedir(ruta("conversations/\(id)"))
        } catch Og118Error.badStatus(404) {
            return nil
        }
        do {
            // El iOS ya dejó `author` como string suelto en la cuenta antes de
            // conocer el contrato: se normaliza en el borde.
            return try JSONDecoder().decode(ConversationRecord.self, from: LegadoDeAutor.normalizar(data))
        } catch let error as DecodingError {
            throw Og118Error.formato(Og118Client.detalle(error))
        }
    }

    func saveConversation(_ record: ConversationRecord) async throws {
        var request = ruta("conversations/\(record.id)", metodo: "PUT")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(record)
        _ = try await pedir(request)
    }

    /// Un reintento tras un borrado que sí llegó contesta 404: ya está borrada.
    func deleteConversation(id: String) async throws {
        do {
            _ = try await pedir(ruta("conversations/\(id)", metodo: "DELETE"))
        } catch Og118Error.badStatus(404) {
        }
    }
}
