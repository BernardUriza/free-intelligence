import Foundation

@MainActor
func autorSeCongelaPorMensaje() async {
    print("el autor queda pegado al mensaje, no al turno")
    let model = ChatModel(stream: canned([
        .open, .author(id: "53", name: "Yodo"), .text("hola"), .done
    ]))
    model.send("uno")
    await settle()

    let model2 = ChatModel(stream: canned([
        .open, .author(id: "1", name: "Hidrogeno"), .text("adios"), .done
    ]))
    model2.send("dos")
    await settle()

    expect(model.messages.count == 2, "un turno deja usuario + asistente")
    expect(model.messages.last?.author?.nombre == "Yodo", "el asistente conserva su autor")
    expect(model.messages.first?.author == nil, "el mensaje del usuario no inventa autor")
    expect(model2.messages.last?.author?.nombre == "Hidrogeno", "otro turno, otro autor")
}

@MainActor
func elResultadoGanaALosDeltas() async {
    print("el frame result reemplaza el texto acumulado")
    let model = ChatModel(stream: canned([
        .text("parcial"), .result(text: "definitivo", model: "sonnet", reactions: []), .done
    ]))
    model.send("x")
    await settle()
    expect(model.messages.last?.content == "definitivo", "gana el result")
    expect(model.isStreaming == false, "el turno cierra")
}

@MainActor
func cancelarNoDuplicaLaBurbuja() async {
    print("cancelar a media respuesta no deja dos burbujas")
    let model = ChatModel(stream: { _, _, _, _, _, _ in
        AsyncThrowingStream { continuation in
            let task = Task {
                for i in 0..<200 {
                    if Task.isCancelled { break }
                    continuation.yield(.text("delta\(i) "))
                    try? await Task.sleep(nanoseconds: 2_000_000)
                }
                continuation.finish()
            }
            continuation.onTermination = { _ in task.cancel() }
        }
    })
    model.send("largo")
    try? await Task.sleep(nanoseconds: 60_000_000)
    model.cancel()
    await settle()

    let asistentes = model.messages.filter { $0.role == .assistant }
    expect(asistentes.count <= 1, "a lo mucho UNA burbuja de asistente (hubo \(asistentes.count))")
    expect(model.isStreaming == false, "isStreaming queda apagado")
    expect(model.liveText.isEmpty, "no queda texto vivo colgado")
}

@MainActor
func elErrorNoInventaBurbuja() async {
    print("un stream que truena no fabrica respuesta")
    let model = ChatModel(stream: { _, _, _, _, _, _ in
        AsyncThrowingStream { continuation in
            continuation.finish(throwing: Og118Error.unauthorized)
        }
    })
    model.send("y")
    await settle()
    expect(model.messages.filter { $0.role == .assistant }.isEmpty, "sin burbuja de asistente")
    expect(model.errorMessage != nil, "el error se le muestra al humano")
}

@MainActor
func elHistorialViajaSinElTurnoNuevo() async {
    print("el history que se manda no incluye el mensaje del turno en curso")
    var vistos: [[ChatMessage]] = []
    let model = ChatModel(stream: { _, _, history, _, _, _ in
        vistos.append(history)
        return AsyncThrowingStream { continuation in
            continuation.yield(.text("respuesta"))
            continuation.finish()
        }
    })
    model.send("viejo")
    await settle()
    model.send("nuevo")
    await settle()

    expect(vistos.first?.isEmpty == true, "el primer turno viaja sin historial")
    expect(vistos.last?.count == 2, "el segundo lleva el par previo (llevó \(vistos.last?.count ?? -1))")
    expect(vistos.last?.contains { $0.content == "nuevo" } == false, "y NO incluye el mensaje en curso")
}

func derivacionesIgualesQueCore() {
    print("título y preview derivan igual que free-intelligence-core")
    expect(ConversationSchema.title([]) == "New chat", "sin mensajes → New chat")
    expect(
        ConversationSchema.title([ChatMessage(role: .assistant, content: "yo hablo primero")]) == "New chat",
        "sin mensaje de usuario → New chat"
    )
    expect(
        ConversationSchema.title([
            ChatMessage(role: .user, content: "  hola   mundo \n raro  ")
        ]) == "hola mundo raro",
        "colapsa espacios y recorta"
    )
    let largo = String(repeating: "a", count: 80)
    let corto = ConversationSchema.title([ChatMessage(role: .user, content: largo)])
    expect(corto.count == 60, "título tope 60 (fue \(corto.count))")
    expect(corto.hasSuffix("…"), "y termina en elipsis")
    expect(
        ConversationSchema.preview([
            ChatMessage(role: .user, content: "primero"),
            ChatMessage(role: .assistant, content: "ultimo"),
            ChatMessage(role: .user, content: "   ")
        ]) == "ultimo",
        "preview = último NO vacío de cualquier rol"
    )
}

@MainActor
func persisteAlCerrarElTurno() async {
    print("el turno se persiste con la forma que el servidor exige")
    var guardados: [ConversationRecord] = []
    let model = ChatModel(
        conversationID: "abc-123",
        stream: canned([.author(id: "53", name: "Yodo"), .text("respuesta"), .done]),
        persist: { guardados.append($0) },
        restore: { _ in nil },
        now: { "2026-08-12T21:00:00Z" }
    )
    await model.restoreThread()
    model.send("pregunta")
    await settle()

    expect(guardados.count == 1, "se guardó una vez al cerrar el turno")
    guard let r = guardados.first else { return }
    expect(r.id == "abc-123", "el id del path es el de la conversación")
    expect(r.schemaVersion == 1, "schemaVersion 1, como core")
    expect(r.messages.count == 2, "usuario + asistente")
    expect(r.title == "pregunta", "título del primer mensaje de usuario")
    expect(r.preview == "respuesta", "preview del último mensaje")
    expect(r.messages.last?.author?.name == "Yodo", "la autoría sobrevive al guardado")
    expect(r.messages.first?.timestamp != nil, "los mensajes llevan timestamp")
}

@MainActor
func elModeloViajaDeIdaYVuelta() async {
    print("el modelo que contestó se escribe en trace.model y se lee de vuelta")
    var guardados: [ConversationRecord] = []
    let model = ChatModel(
        conversationID: "abc-123",
        stream: canned([.text("hola"), .result(text: "hola", model: "claude-sonnet-4-5", reactions: []), .done]),
        persist: { guardados.append($0) },
        restore: { _ in nil },
        now: { "2026-10-10T21:00:00Z" }
    )
    await model.restoreThread()
    model.send("pregunta")
    await settle()

    expect(model.messages.last?.model == "claude-sonnet-4-5", "la burbuja sabe qué modelo la escribió")
    guard let r = guardados.last else { return expect(false, "se guardó el turno") }
    expect(r.messages.last?.trace?.model == "claude-sonnet-4-5", "y viaja en trace.model, donde la web lo lee")
    expect(r.messages.first?.trace == nil, "el mensaje del usuario no inventa trace")
    let releido = try? JSONDecoder().decode(ConversationRecord.self, from: JSONEncoder().encode(r))
    expect(releido?.chatMessages.last?.model == "claude-sonnet-4-5", "y al reabrir el hilo vuelve a la burbuja")
}

@MainActor
func elCorreoSaleDelIdToken() {
    print("el pie del drawer lee el correo del id_token")
    let payload = Data(#"{"email":"bernard@ejemplo.mx","sub":"auth0|1"}"#.utf8)
        .base64EncodedString()
        .replacingOccurrences(of: "=", with: "")
        .replacingOccurrences(of: "+", with: "-")
        .replacingOccurrences(of: "/", with: "_")
    expect(Auth.correo(deIdToken: "cabeza.\(payload).firma") == "bernard@ejemplo.mx", "base64url sin relleno se decodifica")
    expect(Auth.correo(deIdToken: "no-es-jwt") == nil, "un token mal formado no truena, devuelve nil")
}
