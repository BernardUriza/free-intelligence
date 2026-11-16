import Foundation

@MainActor
func restauraElHiloAlArrancar() async {
    print("al arrancar recupera el hilo del servidor")
    let previo = ConversationRecord.from(
        id: "abc-123",
        messages: [
            ChatMessage(role: .user, content: "de ayer"),
            ChatMessage(role: .assistant, content: "te contesté ayer", author: ChatMessage.Autor(id: "53", nombre: "Yodo"))
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
    expect(model.messages.last?.author?.nombre == "Yodo", "con su autoría intacta")
    expect(model.messages.first?.role == .user, "y con los roles bien")
}

@MainActor
func elIdDeConversacionEsElSessionID() async {
    print("el id de conversación viaja como session_id, no uno aleatorio")
    var visto: String?
    let model = ChatModel(
        conversationID: "abc-123",
        stream: { _, sessionID, _, _, _, _ in
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
func cambiarDeHiloNoMezclaMensajes() async {
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
    await model.restoreThread()
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
func laListaAgrupaComoElSidebarWeb() async {
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
func laRedCaidaNoTeDesloguea() async {
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
func elKeychainMudoAvisa() async {
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
func cancelarNoPersisteRespuestaAMedias() async {
    print("cancelar no guarda la respuesta truncada ni la manda como history")
    var guardados: [ConversationRecord] = []
    var historiales: [[ChatMessage]] = []
    let model = ChatModel(
        conversationID: "c1",
        stream: { _, _, history, _, _, _ in
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
    await model.restoreThread()
    model.send("pregunta larga")
    try? await Task.sleep(nanoseconds: 60_000_000)
    model.cancel()
    await settle()

    expect(model.messages.filter { $0.role == .assistant }.isEmpty, "no queda respuesta a medias")
    expect(
        guardados.last?.messages.map(\.content) == ["pregunta larga"],
        "lo guardado es la pregunta sola, sin la respuesta a medias"
    )

    model.send("segunda")
    await settle()
    let ultimo = historiales.last ?? []
    expect(
        ultimo.contains { $0.content.hasPrefix("frag") } == false,
        "el fragmento cancelado NO viaja como history"
    )
}

@MainActor
func losGuardadosNoSePisan() async {
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
    await model.restoreThread()
    model.send("uno")
    await settle()
    model.send("dos")
    await settle()
    try? await Task.sleep(nanoseconds: 300_000_000)

    expect(maxEnVuelo == 1, "nunca hubo dos PUT simultáneos (máximo \(maxEnVuelo))")
    expect(ordenRecibido == [2, 4], "llegaron en orden creciente \(ordenRecibido)")
}

@MainActor
func elElementoYElProyectoViajanEnElTurno() async {
    print("el elemento y el proyecto activos viajan en cada turno")
    var vistos: [(String?, String?)] = []
    let suite = "og118.harness.\(UUID().uuidString)"
    let defaults = UserDefaults(suiteName: suite)!
    defer { UserDefaults.standard.removePersistentDomain(forName: suite) }

    let model = ChatModel(
        conversationID: "c3",
        stream: { _, _, _, corpus, element, _ in
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

func elJSONOmiteLoQueNoSeEligio() {
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
func elSaveNoBorraPinNiRename() async {
    print("guardar un turno NO borra el pin, el archivado ni el rename hechos en la web")
    var persistidos: [ConversationRecord] = []
    let base = ConversationRecord(
        id: "hilo-web",
        title: "Mi título renombrado",
        titleCustom: true,
        createdAt: "2026-08-01T00:00:00Z",
        updatedAt: "2026-08-01T00:00:00Z",
        messages: [PersistedMessage(role: .user, content: "hola")],
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
func mutarUnChatEsLoadEditarSave() async {
    print("fijar/renombrar/archivar cargan el record, editan el campo y re-suben")
    var guardado: ConversationRecord?
    let base = ConversationRecord(
        id: "c1",
        title: "auto",
        titleCustom: nil,
        createdAt: "a",
        updatedAt: "b",
        messages: [PersistedMessage(role: .user, content: "hola tema")],
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
