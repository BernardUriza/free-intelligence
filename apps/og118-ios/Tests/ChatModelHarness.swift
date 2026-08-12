import Foundation

private var failures = 0

private func expect(_ condition: Bool, _ what: String) {
    if condition {
        print("  ok   \(what)")
    } else {
        failures += 1
        print("  FAIL \(what)")
    }
}

private func canned(_ events: [StreamEvent]) -> ChatModel.Stream {
    { _, _, _ in
        AsyncThrowingStream { continuation in
            for event in events { continuation.yield(event) }
            continuation.finish()
        }
    }
}

private func settle() async {
    for _ in 0..<50 { await Task.yield() }
    try? await Task.sleep(nanoseconds: 120_000_000)
}

@MainActor
private func autorSeCongelaPorMensaje() async {
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
    expect(model.messages.last?.author == "Yodo", "el asistente conserva su autor")
    expect(model.messages.first?.author == nil, "el mensaje del usuario no inventa autor")
    expect(model2.messages.last?.author == "Hidrogeno", "otro turno, otro autor")
}

@MainActor
private func elResultadoGanaALosDeltas() async {
    print("el frame result reemplaza el texto acumulado")
    let model = ChatModel(stream: canned([
        .text("parcial"), .result(text: "definitivo", model: "sonnet"), .done
    ]))
    model.send("x")
    await settle()
    expect(model.messages.last?.content == "definitivo", "gana el result")
    expect(model.isStreaming == false, "el turno cierra")
}

@MainActor
private func cancelarNoDuplicaLaBurbuja() async {
    print("cancelar a media respuesta no deja dos burbujas")
    let model = ChatModel(stream: { _, _, _ in
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
private func elErrorNoInventaBurbuja() async {
    print("un stream que truena no fabrica respuesta")
    let model = ChatModel(stream: { _, _, _ in
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
private func elHistorialViajaSinElTurnoNuevo() async {
    print("el history que se manda no incluye el mensaje del turno en curso")
    var vistos: [[ChatMessage]] = []
    let model = ChatModel(stream: { _, _, history in
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

private func derivacionesIgualesQueCore() {
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
private func persisteAlCerrarElTurno() async {
    print("el turno se persiste con la forma que el servidor exige")
    var guardados: [ConversationRecord] = []
    let model = ChatModel(
        conversationID: "abc-123",
        stream: canned([.author(id: "53", name: "Yodo"), .text("respuesta"), .done]),
        persist: { guardados.append($0) },
        restore: { _ in nil },
        now: { "2026-08-12T21:00:00Z" }
    )
    model.send("pregunta")
    await settle()

    expect(guardados.count == 1, "se guardó una vez al cerrar el turno")
    guard let r = guardados.first else { return }
    expect(r.id == "abc-123", "el id del path es el de la conversación")
    expect(r.schemaVersion == 1, "schemaVersion 1, como core")
    expect(r.messages.count == 2, "usuario + asistente")
    expect(r.title == "pregunta", "título del primer mensaje de usuario")
    expect(r.preview == "respuesta", "preview del último mensaje")
    expect(r.messages.last?.author == "Yodo", "la autoría sobrevive al guardado")
    expect(r.messages.first?.timestamp != nil, "los mensajes llevan timestamp")
}

@MainActor
private func restauraElHiloAlArrancar() async {
    print("al arrancar recupera el hilo del servidor")
    let previo = ConversationRecord.from(
        id: "abc-123",
        messages: [
            ChatMessage(role: .user, content: "de ayer"),
            ChatMessage(role: .assistant, content: "te contesté ayer", author: "Yodo")
        ],
        createdAt: "2026-08-11T10:00:00Z",
        now: "2026-08-11T10:00:05Z"
    )
    let model = ChatModel(
        conversationID: "abc-123",
        stream: canned([.done]),
        persist: { _ in },
        restore: { _ in previo },
        now: { "2026-08-12T21:00:00Z" }
    )
    await model.restoreThread()

    expect(model.messages.count == 2, "el hilo vuelve (llegaron \(model.messages.count))")
    expect(model.messages.last?.author == "Yodo", "con su autoría intacta")
    expect(model.messages.first?.role == .user, "y con los roles bien")
}

@MainActor
private func elIdDeConversacionEsElSessionID() async {
    print("el id de conversación viaja como session_id, no uno aleatorio")
    var visto: String?
    let model = ChatModel(
        conversationID: "abc-123",
        stream: { _, sessionID, _ in
            visto = sessionID
            return AsyncThrowingStream { $0.finish() }
        },
        now: { "2026-08-12T21:00:00Z" }
    )
    model.send("x")
    await settle()
    expect(visto == "abc-123", "session_id == id de conversación (fue \(visto ?? "nil"))")
}

@MainActor
private func cambiarDeHiloNoMezclaMensajes() async {
    print("abrir otro hilo no arrastra los mensajes del anterior")
    let otro = ConversationRecord.from(
        id: "hilo-b",
        messages: [ChatMessage(role: .user, content: "soy el hilo B")],
        createdAt: "2026-08-10T10:00:00Z",
        now: "2026-08-10T10:00:01Z"
    )
    let model = ChatModel(
        conversationID: "hilo-a",
        stream: canned([.text("respuesta de A"), .done]),
        persist: { _ in },
        restore: { id in id == "hilo-b" ? otro : nil },
        now: { "2026-08-12T21:00:00Z" }
    )
    model.send("hola A")
    await settle()
    expect(model.messages.count == 2, "el hilo A tiene su par")

    await model.open("hilo-b")
    expect(model.conversationID == "hilo-b", "cambió el id activo")
    expect(model.messages.count == 1, "sólo lo del hilo B (hubo \(model.messages.count))")
    expect(model.messages.first?.content == "soy el hilo B", "y es el contenido de B")

    model.startNew()
    expect(model.messages.isEmpty, "una conversación nueva arranca vacía")
    expect(model.conversationID != "hilo-b", "y con id distinto")
}

@MainActor
private func laListaEscondeLosArchivados() async {
    print("la lista oculta los archivados")
    let modelo = ConversationsModel(list: {
        [
            ConversationSummary(id: "1", title: "viva", createdAt: "a", updatedAt: "b", preview: "x", pinnedAt: nil, archivedAt: nil),
            ConversationSummary(id: "2", title: "archivada", createdAt: "a", updatedAt: "b", preview: "x", pinnedAt: nil, archivedAt: "2026-08-01T00:00:00Z")
        ]
    })
    await modelo.refresh()
    expect(modelo.summaries.count == 1, "sólo la viva (quedaron \(modelo.summaries.count))")
    expect(modelo.summaries.first?.id == "1", "y es la correcta")
}

@MainActor
private func laRedCaidaNoTeDesloguea() async {
    print("perder la red NO borra la sesión; un rechazo de Auth0 sí")
    var guardado: String? = "refresh-viejo"
    func deps(_ fallo: AuthError) -> AuthDependencies {
        AuthDependencies(
            exchange: { _ in throw fallo },
            keychainRead: { guardado },
            keychainSave: { guardado = $0; return true },
            keychainDelete: { guardado = nil }
        )
    }

    let sinRed = Auth(deps: deps(.transport("The Internet connection appears to be offline.")))
    expect(sinRed.isSignedIn, "arranca con sesión restaurada del Keychain")
    do { _ = try await sinRed.token(); expect(false, "debía fallar") } catch {}
    expect(sinRed.isSignedIn, "SIGUE con sesión tras un fallo de red")
    expect(guardado != nil, "el refresh token SIGUE en el Keychain")

    guardado = "refresh-revocado"
    let revocado = Auth(deps: deps(.rejected(403)))
    do { _ = try await revocado.token(); expect(false, "debía fallar") } catch {}
    expect(revocado.isSignedIn == false, "un 403 sí cierra la sesión")
    expect(guardado == nil, "y sí limpia el Keychain")

    expect(AuthError.transport("x").revokesSession == false, "transporte no revoca")
    expect(AuthError.rejected(401).revokesSession, "401 revoca")
    expect(AuthError.rejected(500).revokesSession == false, "un 500 del servidor NO revoca")
}

@MainActor
private func elKeychainMudoAvisa() async {
    print("si el Keychain no guarda, el usuario se entera")
    let auth = Auth(deps: AuthDependencies(
        exchange: { _ in TokenResponse(accessToken: "at", refreshToken: "rt", expiresIn: 3600) },
        keychainRead: { "previo" },
        keychainSave: { _ in false },
        keychainDelete: {}
    ))
    _ = try? await auth.token()
    expect(auth.storageWarning != nil, "hay aviso cuando el guardado falla")
    expect(auth.isSignedIn, "pero la sesión de esta corrida sigue viva")
}

@MainActor
private func cancelarNoPersisteRespuestaAMedias() async {
    print("cancelar no guarda la respuesta truncada ni la manda como history")
    var guardados: [ConversationRecord] = []
    var historiales: [[ChatMessage]] = []
    let model = ChatModel(
        conversationID: "c1",
        stream: { _, _, history in
            historiales.append(history)
            return AsyncThrowingStream { continuation in
                let t = Task {
                    for i in 0..<200 {
                        if Task.isCancelled { break }
                        continuation.yield(.text("frag\(i) "))
                        try? await Task.sleep(nanoseconds: 2_000_000)
                    }
                    continuation.finish()
                }
                continuation.onTermination = { _ in t.cancel() }
            }
        },
        persist: { guardados.append($0) },
        restore: { _ in nil },
        now: { "2026-08-12T22:00:00Z" }
    )
    model.send("pregunta larga")
    try? await Task.sleep(nanoseconds: 60_000_000)
    model.cancel()
    await settle()

    expect(model.messages.filter { $0.role == .assistant }.isEmpty, "no queda respuesta a medias")
    expect(guardados.isEmpty, "y NO se persistió nada del turno cancelado")

    model.send("segunda")
    await settle()
    let ultimo = historiales.last ?? []
    expect(
        ultimo.contains { $0.content.hasPrefix("frag") } == false,
        "el fragmento cancelado NO viaja como history"
    )
}

@MainActor
private func losGuardadosNoSePisan() async {
    print("dos turnos seguidos guardan EN ORDEN, nunca en paralelo")
    var enVuelo = 0
    var maxEnVuelo = 0
    var ordenRecibido: [Int] = []
    let model = ChatModel(
        conversationID: "c2",
        stream: canned([.text("r"), .done]),
        persist: { record in
            enVuelo += 1
            maxEnVuelo = max(maxEnVuelo, enVuelo)
            let n = record.messages.count
            try? await Task.sleep(nanoseconds: UInt64((6 - n) * 20_000_000))
            ordenRecibido.append(n)
            enVuelo -= 1
        },
        restore: { _ in nil },
        now: { "2026-08-12T22:00:00Z" }
    )
    model.send("uno")
    await settle()
    model.send("dos")
    await settle()
    try? await Task.sleep(nanoseconds: 300_000_000)

    expect(maxEnVuelo == 1, "nunca hubo dos PUT simultáneos (máximo \(maxEnVuelo))")
    expect(ordenRecibido == [2, 4], "llegaron en orden creciente \(ordenRecibido)")
}

@main
struct Harness {
    static func main() async {
        print("ChatModel — arnés de verificación (sin Xcode)")
        await autorSeCongelaPorMensaje()
        await elResultadoGanaALosDeltas()
        await cancelarNoDuplicaLaBurbuja()
        await elErrorNoInventaBurbuja()
        await elHistorialViajaSinElTurnoNuevo()
        derivacionesIgualesQueCore()
        await persisteAlCerrarElTurno()
        await restauraElHiloAlArrancar()
        await elIdDeConversacionEsElSessionID()
        await cambiarDeHiloNoMezclaMensajes()
        await laListaEscondeLosArchivados()
        await laRedCaidaNoTeDesloguea()
        await elKeychainMudoAvisa()
        await cancelarNoPersisteRespuestaAMedias()
        await losGuardadosNoSePisan()
        print(failures == 0 ? "\nTODO VERDE" : "\n\(failures) FALLARON")
        exit(failures == 0 ? 0 : 1)
    }
}
