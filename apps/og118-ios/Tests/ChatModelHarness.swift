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
    { _, _, _, _, _ in
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
    let model = ChatModel(stream: { _, _, _, _, _ in
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
    let model = ChatModel(stream: { _, _, _, _, _ in
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
    let model = ChatModel(stream: { _, _, history, _, _ in
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
        stream: { _, sessionID, _, _, _ in
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
private func laListaAgrupaComoElSidebarWeb() async {
    print("la lista agrupa como el sidebar web: fijados, chats, archivados")
    let modelo = ConversationsModel(list: {
        [
            ConversationSummary(id: "1", title: "viva", createdAt: "a", updatedAt: "2026-08-02T00:00:00Z", preview: "x", pinnedAt: nil, archivedAt: nil),
            ConversationSummary(id: "2", title: "archivada", createdAt: "a", updatedAt: "b", preview: "x", pinnedAt: nil, archivedAt: "2026-08-01T00:00:00Z"),
            ConversationSummary(id: "3", title: "fijada", createdAt: "a", updatedAt: "2026-08-01T00:00:00Z", preview: "x", pinnedAt: "2026-08-03T00:00:00Z", archivedAt: nil)
        ]
    })
    await modelo.refresh()
    expect(modelo.summaries.count == 3, "el refresh conserva TODO (hay \(modelo.summaries.count))")
    expect(modelo.active.map(\.id) == ["1"], "Chats sólo trae la viva sin fijar")
    expect(modelo.pinned.map(\.id) == ["3"], "Fijados trae la fijada")
    expect(modelo.archived.map(\.id) == ["2"], "Archivados trae la archivada")
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
        stream: { _, _, history, _, _ in
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

@MainActor
private func elElementoYElProyectoViajanEnElTurno() async {
    print("el elemento y el proyecto activos viajan en cada turno")
    var vistos: [(String?, String?)] = []
    let suite = "og118.harness.\(UUID().uuidString)"
    let defaults = UserDefaults(suiteName: suite)!
    defer { UserDefaults.standard.removePersistentDomain(forName: suite) }

    let model = ChatModel(
        conversationID: "c3",
        stream: { _, _, _, corpus, element in
            vistos.append((corpus, element))
            return AsyncThrowingStream { continuation in
                continuation.yield(.text("r"))
                continuation.finish()
            }
        },
        now: { "2026-08-12T23:00:00Z" },
        defaults: defaults
    )

    model.send("sin contexto")
    await settle()
    expect(vistos.last?.0 == nil && vistos.last?.1 == nil, "sin selección no viaja nada")

    model.element = "yodo"
    model.corpusID = "project-abc"
    model.send("con contexto")
    await settle()
    expect(vistos.last?.1 == "yodo", "viaja el elemento (fue \(vistos.last?.1 ?? "nil"))")
    expect(vistos.last?.0 == "project-abc", "viaja el corpus (fue \(vistos.last?.0 ?? "nil"))")
}

private func elJSONOmiteLoQueNoSeEligio() {
    print("el JSON omite element/corpus_id cuando no hay selección")
    struct Sonda: Encodable {
        let message: String
        let sessionID: String
        let corpusID: String?
        let element: String?
        enum CodingKeys: String, CodingKey {
            case message
            case element
            case sessionID = "session_id"
            case corpusID = "corpus_id"
        }
    }
    let enc = JSONEncoder()
    let vacio = String(data: try! enc.encode(Sonda(message: "m", sessionID: "s", corpusID: nil, element: nil)), encoding: .utf8)!
    let lleno = String(data: try! enc.encode(Sonda(message: "m", sessionID: "s", corpusID: "p1", element: "yodo")), encoding: .utf8)!
    expect(!vacio.contains("element"), "sin elemento la clave NO aparece (no manda null)")
    expect(!vacio.contains("corpus_id"), "sin proyecto la clave NO aparece")
    expect(lleno.contains("\"element\":\"yodo\""), "con elemento sí aparece")
    expect(lleno.contains("\"corpus_id\":\"p1\""), "con proyecto sí aparece")
}

@MainActor
private func elSaveNoBorraPinNiRename() async {
    print("guardar un turno NO borra el pin, el archivado ni el rename hechos en la web")
    var persistidos: [ConversationRecord] = []
    let base = ConversationRecord(
        id: "hilo-web",
        title: "Mi título renombrado",
        titleCustom: true,
        createdAt: "2026-08-01T00:00:00Z",
        updatedAt: "2026-08-01T00:00:00Z",
        messages: [PersistedMessage(role: "user", content: "hola", timestamp: nil, author: nil)],
        preview: "hola",
        pinnedAt: "2026-08-02T00:00:00Z",
        archivedAt: nil,
        schemaVersion: 1
    )
    let model = ChatModel(
        conversationID: "hilo-web",
        stream: canned([.open, .text("respuesta"), .done]),
        persist: { persistidos.append($0) },
        restore: { _ in base }
    )
    await model.restoreThread()
    model.send("otro turno")
    await settle()

    expect(persistidos.count == 1, "hubo exactamente un PUT")
    expect(persistidos.first?.pinnedAt == "2026-08-02T00:00:00Z", "el pin sobrevive al PUT")
    expect(persistidos.first?.titleCustom == true, "titleCustom sobrevive")
    expect(persistidos.first?.title == "Mi título renombrado", "el título renombrado NO se re-deriva")
}

@MainActor
private func mutarUnChatEsLoadEditarSave() async {
    print("fijar/renombrar/archivar cargan el record, editan el campo y re-suben")
    var guardado: ConversationRecord?
    let base = ConversationRecord(
        id: "c1",
        title: "auto",
        titleCustom: nil,
        createdAt: "a",
        updatedAt: "b",
        messages: [PersistedMessage(role: "user", content: "hola tema", timestamp: nil, author: nil)],
        preview: "hola tema",
        pinnedAt: nil,
        archivedAt: nil,
        schemaVersion: 1
    )
    let modelo = ConversationsModel(
        list: { [] },
        load: { _ in guardado ?? base },
        save: { guardado = $0 },
        now: { "2026-08-12T00:00:00Z" }
    )

    _ = await modelo.setPinned("c1", true)
    expect(guardado?.pinnedAt == "2026-08-12T00:00:00Z", "el pin viaja con timestamp")

    _ = await modelo.setArchived("c1", true)
    expect(guardado?.archivedAt == "2026-08-12T00:00:00Z", "archivar viaja con timestamp")
    expect(guardado?.pinnedAt == "2026-08-12T00:00:00Z", "y NO borra el pin previo")

    _ = await modelo.rename("c1", to: "Nuevo nombre")
    expect(guardado?.title == "Nuevo nombre", "el rename cambia el título")
    expect(guardado?.titleCustom == true, "y lo marca custom")

    _ = await modelo.rename("c1", to: "  ")
    expect(guardado?.title == "hola tema", "rename vacío regresa al título derivado")
    expect(guardado?.titleCustom == nil, "y quita la marca custom")
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
        await laListaAgrupaComoElSidebarWeb()
        await laRedCaidaNoTeDesloguea()
        await elKeychainMudoAvisa()
        await cancelarNoPersisteRespuestaAMedias()
        await losGuardadosNoSePisan()
        await elElementoYElProyectoViajanEnElTurno()
        elJSONOmiteLoQueNoSeEligio()
        await elSaveNoBorraPinNiRename()
        await mutarUnChatEsLoadEditarSave()
        await elPlanYLosPasosSePintan()
        await nadaDesaparecEnSilencio()
        await elPlanNoSeArrastraEntreTurnos()
        elMarkdownPegadoSeRepara()
        await elTurnoVacioSeDeclara()
        await elTurnoBuenoNoOfreceReintento()
        await reintentarNoDuplicaLaBurbujaDelUsuario()
        await cancelarNoOfreceReintento()
        elParserLeeUnTurnoDeVerdad()
        elParserAguantaLoQueElServidorPuedeMandar()
        laSondaNoSeDisparaSola()
        print(failures == 0 ? "\nTODO VERDE" : "\n\(failures) FALLARON")
        exit(failures == 0 ? 0 : 1)
    }
}

// MARK: - Plan glass-box: los frames que antes caían en `break`

@MainActor
private func elPlanYLosPasosSePintan() async {
    print("el plan del agente deja de tirarse a la basura")
    let model = ChatModel(stream: canned([
        .open,
        .plan(["Buscar", "Resumir"]),
        .stepStarted(0),
        .stepNoted(index: 0, note: "encontré 3 fuentes"),
        .stepDone(index: 0, status: .done, summary: "listo", error: nil),
        .stepDone(index: 1, status: .failed, summary: nil, error: "timeout"),
        // El servidor manda el índice que quiere; el cliente no lo controla.
        .stepStarted(99),
        .text("ya"), .done
    ]))
    model.send("x")
    await settle()

    // Indexar crudo aquí abortaba el arnés completo y escondía cada prueba
    // posterior: un assert debe poder fallar sin matar a sus vecinos.
    let pasos = model.plan.pasos
    expect(pasos.count == 2, "el plan declara sus pasos (hubo \(pasos.count))")
    expect(pasos.first?.estado == .hecho, "step_done cierra el paso")
    expect(pasos.first?.nota == "encontré 3 fuentes", "step_noted guarda la nota")
    expect(pasos.first?.detalle == "listo", "el resumen queda visible")
    expect(pasos.last?.estado == .fallido, "un paso puede fallar")
    expect(pasos.last?.detalle == "timeout", "el error le gana al resumen")
}

@MainActor
private func nadaDesaparecEnSilencio() async {
    print("un frame desconocido se muestra en vez de evaporarse")
    let model = ChatModel(stream: canned([
        .open,
        .toolCall(name: "read", server: "fs", isError: false),
        .toolCall(name: "web", server: nil, isError: true),
        .unmapped("thinking"),
        .text("ok"), .done
    ]))
    model.send("x")
    await settle()

    expect(model.herramientas.contains("fs/read"), "la herramienta se nombra servidor/nombre")
    expect(model.herramientas.contains("web ✗"), "una herramienta con error se marca")
    expect(model.herramientas.contains { $0.contains("thinking") },
           "un frame sin mapear queda registrado, no se tira")
}

@MainActor
private func elPlanNoSeArrastraEntreTurnos() async {
    print("cada turno arranca con el plan limpio")
    // Dos turnos en EL MISMO modelo: es la única forma de probar el reset.
    var guion: [[StreamEvent]] = [
        [.open, .plan(["a"]), .toolCall(name: "t", server: nil, isError: false), .text("1"), .done],
        [.open, .text("2"), .done]
    ]
    let model = ChatModel(stream: { _, _, _, _, _ in
        let eventos = guion.isEmpty ? [] : guion.removeFirst()
        return AsyncThrowingStream { c in
            for e in eventos { c.yield(e) }
            c.finish()
        }
    })
    model.send("uno")
    await settle()
    expect(model.plan.pasos.count == 1, "el primer turno dejó su plan")

    model.send("dos")
    await settle()
    expect(model.plan.vacio, "el segundo turno no hereda el plan del primero")
    expect(model.herramientas.isEmpty, "ni las herramientas del primero")
}

private func laSondaNoSeDisparaSola() {
    print("la sonda de turno NO existe sin su bandera")
    expect(SondaDeTurno.pedida([]) == false, "sin argumentos no hay sonda")
    expect(SondaDeTurno.pedida(["/App", "-NSTreatUnknownArgumentsAsOpen", "YES"]) == false,
           "los argumentos normales de un lanzamiento no la disparan")
    expect(SondaDeTurno.pedida(["/App", "--sonda"]), "con la bandera sí")
}

// MARK: - El parser contra BYTES REALES del servidor

private func elParserLeeUnTurnoDeVerdad() {
    print("SSEParser contra la captura real de /chat/stream")
    // Capturado con curl contra el server og118 corriendo local, mismo código
    // que el de Azure. Si el contrato del servidor cambia, esto se pone rojo
    // aquí y no en el teléfono de Bernard.
    let ruta = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .appendingPathComponent("Fixtures/turno-real.sse")
    guard let crudo = try? String(contentsOf: ruta, encoding: .utf8) else {
        expect(false, "la captura real existe en Tests/Fixtures/turno-real.sse")
        return
    }

    func correr(_ lineas: [String]) -> [StreamEvent] {
        var parser = SSEParser()
        var eventos: [StreamEvent] = []
        for linea in lineas {
            if let e = parser.feed(linea) { eventos.append(e) }
        }
        if let ultimo = parser.cerrar() { eventos.append(ultimo) }
        return eventos
    }

    let todas = crudo.components(separatedBy: "\n")
    let eventos = correr(todas)
    expect(eventos.count == 4, "salieron los 4 frames del turno (fueron \(eventos.count))")

    // EL BUG REAL: `URLSession.AsyncBytes.lines` se traga las líneas en blanco,
    // así que el turno llega SIN separadores. Con el parser viejo esto daba 0
    // frames y la app se quedaba muda con el texto ya recibido.
    let sinBlancos = todas.filter { !$0.isEmpty }
    let eventosSinBlancos = correr(sinBlancos)
    expect(eventosSinBlancos.count == 4,
           "sin líneas en blanco TAMBIÉN salen los 4 frames (fueron \(eventosSinBlancos.count))")

    var abrio = false, texto: String?, resultado: String?, modelo: String?, cerro = false
    for e in eventos {
        switch e {
        case .open: abrio = true
        case .text(let t): texto = t
        case .result(let t, let m): resultado = t; modelo = m
        case .done: cerro = true
        default: break
        }
    }
    expect(abrio, "el frame open se reconoce")
    expect(texto == "PONG", "el delta de texto llega íntegro")
    expect(resultado == "PONG", "el result trae el texto definitivo")
    expect(modelo == "claude-sonnet-4-5", "y el modelo que de verdad contestó")
    expect(cerro, "el done cierra el turno")
}

private func elParserAguantaLoQueElServidorPuedeMandar() {
    print("SSEParser: los casos que el servidor sí produce")
    var p1 = SSEParser()
    // Un frame partido en dos líneas data: — SSE lo permite y el servidor
    // podría hacerlo si un payload creciera.
    _ = p1.feed("data: {\"type\": \"te")
    _ = p1.feed("data: xt\", \"text\": \"hola\"}")
    if case .text(let t)? = p1.feed("") {
        expect(t == "hola", "un frame partido en dos líneas se reensambla")
    } else {
        expect(false, "un frame partido en dos líneas se reensambla")
    }

    var p2 = SSEParser()
    expect(p2.feed("") == nil, "una línea en blanco suelta no inventa frame")
    expect(p2.feed(": comentario") == nil, "un comentario SSE se ignora")
    expect(p2.feed("event: message") == nil, "una línea event: no rompe nada")

    var p3 = SSEParser()
    _ = p3.feed("data: {\"type\": \"done\"}")
    expect(p3.cerrar() != nil, "un stream que corta sin línea final NO pierde el último frame")
}

// MARK: - El turno que muere en silencio

@MainActor
private func elTurnoVacioSeDeclara() async {
    print("un turno sin texto deja de verse igual que uno pensando")
    let model = ChatModel(stream: canned([]))
    model.send("hola")
    await settle()
    expect(model.errorMessage?.contains("sin mandar un solo frame") == true,
           "cero frames se nombra como tal")
    expect(model.reintentable == "hola", "el mensaje queda listo para reintentar")
    expect(model.messages.count == 1, "y NO se inventa una burbuja de asistente")

    let conFrames = ChatModel(stream: canned([.open, .stepStarted(0), .done]))
    conFrames.send("hola")
    await settle()
    expect(conFrames.errorMessage?.contains("3 frames") == true,
           "con frames pero sin texto, se dice cuántos llegaron")
}

@MainActor
private func elTurnoBuenoNoOfreceReintento() async {
    print("un turno que sí contesta no ensucia la pantalla")
    let model = ChatModel(stream: canned([.open, .text("hola"), .done]))
    model.send("x")
    await settle()
    expect(model.errorMessage == nil, "sin error")
    expect(model.reintentable == nil, "sin botón de reintentar")
}

@MainActor
private func reintentarNoDuplicaLaBurbujaDelUsuario() async {
    print("reintentar rehace el turno, no el mensaje")
    var guion: [[StreamEvent]] = [[], [.open, .text("ahora sí"), .done]]
    var historiasVistas: [[ChatMessage]] = []
    let model = ChatModel(stream: { _, _, history, _, _ in
        historiasVistas.append(history)
        let eventos = guion.isEmpty ? [] : guion.removeFirst()
        return AsyncThrowingStream { c in
            for e in eventos { c.yield(e) }
            c.finish()
        }
    })
    model.send("hola")
    await settle()
    model.reintentar()
    await settle()

    expect(model.messages.filter { $0.role == .user }.count == 1,
           "el usuario sigue teniendo UN solo mensaje")
    expect(model.messages.last?.content == "ahora sí", "y ya tiene su respuesta")
    expect(model.errorMessage == nil, "el error del intento muerto se limpia")
    expect(model.reintentable == nil, "y el botón desaparece")
    expect(historiasVistas.count == 2, "hubo dos llamadas al servidor (hubo \(historiasVistas.count))")
    expect(historiasVistas.last?.contains { $0.content == "hola" } == false,
           "el reintento NO manda el mensaje nuevo dentro del historial")
}

@MainActor
private func cancelarNoOfreceReintento() async {
    print("cancelar es una decisión, no una falla")
    let model = ChatModel(stream: { _, _, _, _, _ in
        AsyncThrowingStream { c in c.yield(.open) }
    })
    model.send("hola")
    await settle()
    model.cancel()
    await settle()
    expect(model.reintentable == nil, "lo que cancelaste no te pide reintentar")
    expect(model.errorMessage == nil, "ni te acusa de un error que no hubo")
}

// MARK: - normalizeStreamedMarkdown portado de fi-glass

private func elMarkdownPegadoSeRepara() {
    print("normalizeStreamedMarkdown: repara sin inventar")
    let n = StreamedMarkdown.normalize
    expect(n("fin.## Título") == "fin.\n\n## Título",
           "un encabezado pegado a puntuación se despega")
    expect(n("necesarias:### Sub") == "necesarias:\n\n### Sub",
           "también tras dos puntos")

    // Los falsos positivos que la regla conservadora debe respetar.
    expect(n("C# is nice") == "C# is nice", "C# queda intacto")
    expect(n("issue #123") == "issue #123", "una referencia a issue queda intacta")
    expect(n("use the # key") == "use the # key", "un gato suelto queda intacto")
    expect(n("# Título") == "# Título", "un encabezado que ya está bien no se toca")
    expect(n("línea\n## Título") == "línea\n## Título",
           "un encabezado que ya empieza renglón no se toca")

    // Dentro de un fence NADA se toca: ahí el gato es sintaxis.
    let code = "```\nfin.## no tocar\n```"
    expect(n(code) == code, "el interior de un fence queda intacto")
    // Un fence sin cerrar es el estado NORMAL a media transmisión.
    let abierto = "texto.## Sí\n```\nfin.## no"
    expect(n(abierto) == "texto.\n\n## Sí\n```\nfin.## no",
           "con el fence abierto sólo se repara lo de afuera")
}
