import Foundation
import ImageIO
import UniformTypeIdentifiers

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
    { _, _, _, _, _, _ in
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
    expect(model.messages.last?.author?.nombre == "Yodo", "el asistente conserva su autor")
    expect(model.messages.first?.author == nil, "el mensaje del usuario no inventa autor")
    expect(model2.messages.last?.author?.nombre == "Hidrogeno", "otro turno, otro autor")
}

@MainActor
private func elResultadoGanaALosDeltas() async {
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
private func cancelarNoDuplicaLaBurbuja() async {
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
private func elErrorNoInventaBurbuja() async {
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
private func elHistorialViajaSinElTurnoNuevo() async {
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
private func elModeloViajaDeIdaYVuelta() async {
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
private func elCorreoSaleDelIdToken() {
    print("el pie del drawer lee el correo del id_token")
    let payload = Data(#"{"email":"bernard@ejemplo.mx","sub":"auth0|1"}"#.utf8)
        .base64EncodedString()
        .replacingOccurrences(of: "=", with: "")
        .replacingOccurrences(of: "+", with: "-")
        .replacingOccurrences(of: "/", with: "_")
    expect(Auth.correo(deIdToken: "cabeza.\(payload).firma") == "bernard@ejemplo.mx", "base64url sin relleno se decodifica")
    expect(Auth.correo(deIdToken: "no-es-jwt") == nil, "un token mal formado no truena, devuelve nil")
}

@MainActor
private func restauraElHiloAlArrancar() async {
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
private func elIdDeConversacionEsElSessionID() async {
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
private func elElementoYElProyectoViajanEnElTurno() async {
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
private func mutarUnChatEsLoadEditarSave() async {
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


// MARK: - Adjuntar imágenes (paridad con useComposerImages de fi-glass)

private func imagenDePrueba(ancho: Int, alto: Int, ruido: Bool, tipo: UTType) -> Data {
    let contexto = CGContext(
        data: nil, width: ancho, height: alto, bitsPerComponent: 8, bytesPerRow: 0,
        space: CGColorSpace(name: CGColorSpace.sRGB)!,
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    )!
    contexto.setFillColor(CGColor(red: 0.2, green: 0.8, blue: 0.6, alpha: 1))
    contexto.fill(CGRect(x: 0, y: 0, width: ancho, height: alto))
    if ruido, let pixeles = contexto.data?.assumingMemoryBound(to: UInt8.self) {
        var semilla: UInt32 = 118
        for i in 0..<(contexto.bytesPerRow * alto) {
            semilla = semilla &* 1_664_525 &+ 1_013_904_223
            pixeles[i] = UInt8(truncatingIfNeeded: semilla >> 24)
        }
    }
    let salida = NSMutableData()
    let destino = CGImageDestinationCreateWithData(salida, tipo.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(destino, contexto.makeImage()!, nil)
    CGImageDestinationFinalize(destino)
    return salida as Data
}

private func dimensiones(_ base64: String) -> (Int, Int)? {
    guard let datos = Data(base64Encoded: base64),
          let fuente = CGImageSourceCreateWithData(datos as CFData, nil),
          let props = CGImageSourceCopyPropertiesAtIndex(fuente, 0, nil) as? [CFString: Any],
          let w = props[kCGImagePropertyPixelWidth] as? Int,
          let h = props[kCGImagePropertyPixelHeight] as? Int else { return nil }
    return (w, h)
}

private func imagenAdjuntaComoLaWeb() {
    print("adjuntar: mismos tipos, reducción y rechazos que fi-glass")
    let chica = imagenDePrueba(ancho: 300, alto: 200, ruido: false, tipo: .png)
    let png = try? ImagenAdjunta.preparar(chica, nombre: "captura.png")
    expect(png?.mediaType == "image/png", "un PNG chico viaja como PNG (conserva transparencia)")
    expect(png?.data == chica.base64EncodedString(), "y byte por byte, sin pasar por el canvas")

    let grande = imagenDePrueba(ancho: 4000, alto: 3000, ruido: true, tipo: .png)
    expect(grande.count > ImagenAdjunta.bytesSinTocar, "control: la foto de prueba sí pesa más del umbral (\(grande.count) bytes)")
    let reducida = try? ImagenAdjunta.preparar(grande, nombre: "foto.png")
    expect(reducida?.mediaType == "image/jpeg", "una foto pesada se re-codifica a JPEG")
    let lados = reducida.flatMap { dimensiones($0.data) }
    expect(lados.map { max($0.0, $0.1) } == ImagenAdjunta.ladoMaximo, "con el lado mayor en 2048 (llegó \(lados.map { "\($0.0)×\($0.1)" } ?? "nada"))")
    expect((reducida?.data.count ?? .max) <= ImagenAdjunta.maximoBase64, "y bajo el techo de 4 MiB de base64")

    let heic = imagenDePrueba(ancho: 600, alto: 400, ruido: false, tipo: .heic)
    expect((try? ImagenAdjunta.preparar(heic))?.mediaType == "image/jpeg", "el HEIC de la cámara (que el servidor rechaza) sale como JPEG")

    do {
        _ = try ImagenAdjunta.preparar(Data("no soy imagen".utf8), nombre: "nota.txt")
        expect(false, "basura debería rechazarse")
    } catch {
        expect((error as? ImagenAdjunta.Rechazo) == .ilegible("nota.txt"), "basura se rechaza con el mensaje de la web")
    }
}

@MainActor
private func adjuntosTopanEnCuatro() async {
    print("adjuntos: el quinto se rechaza con el mensaje de la web")
    let modelo = AdjuntosModel()
    let chica = imagenDePrueba(ancho: 40, alto: 40, ruido: false, tipo: .png)
    await modelo.agregar((1...5).map { AdjuntosModel.Archivo(datos: chica, nombre: "f\($0).png") })
    expect(modelo.borradores.count == 4, "se quedan 4 (hay \(modelo.borradores.count))")
    expect(modelo.error == "Máximo 4 imágenes por mensaje.", "y el quinto avisa, no desaparece en silencio")
    expect(modelo.lugaresLibres == 0, "sin lugares libres el + se deshabilita")
}

@MainActor
private func laImagenViajaYSePersiste() async {
    print("una imagen viaja en el turno, se guarda en el record y no se re-sube en history")
    var imagenesEnviadas: [[MessageImage]] = []
    var historias: [[ChatMessage]] = []
    var guardados: [ConversationRecord] = []
    let foto = MessageImage(mediaType: "image/png", data: "iVBORw0KGgo=")
    let model = ChatModel(
        conversationID: "img-1",
        stream: { _, _, history, _, _, images in
            imagenesEnviadas.append(images)
            historias.append(history)
            return AsyncThrowingStream { c in c.yield(.text("veo un gato")); c.yield(.done); c.finish() }
        },
        persist: { guardados.append($0) },
        restore: { _ in nil },
        now: { "2026-10-10T22:00:00Z" }
    )
    await model.restoreThread()
    model.send("   ", images: [foto])
    await settle()
    expect(imagenesEnviadas.first?.first?.data == foto.data, "un envío de SÓLO imagen sale (la foto es el mensaje)")
    expect(model.messages.first?.images.count == 1, "la burbuja del usuario lleva su imagen")
    expect(guardados.last?.messages.first?.images?.first?.mediaType == "image/png", "el record guarda la imagen")
    expect(guardados.last?.title == ConversationSchema.defaultTitle, "un hilo que empieza con foto toma el título por defecto, como core")

    model.send("¿y ahora?")
    await settle()
    expect(imagenesEnviadas.last?.isEmpty == true, "el turno siguiente no re-sube la foto")
    let cuerpo = String(data: (try? JSONEncoder().encode(historias.last ?? [])) ?? Data(), encoding: .utf8) ?? ""
    expect(!cuerpo.contains("iVBORw0KGgo"), "ni la mete en history")

    let releido = try? JSONDecoder().decode(ConversationRecord.self, from: JSONEncoder().encode(guardados.last!))
    expect(releido?.chatMessages.first?.images.first?.data == foto.data, "al reabrir, la imagen vuelve a la burbuja")

    let peticion = ChatRequest(message: "", sessionID: "img-1", history: [], corpusID: nil, element: nil,
                               images: [ImagenDelTurno(mediaType: foto.mediaType, data: foto.data)])
    try? JSONEncoder().encode(peticion).write(to: URL(fileURLWithPath: "/tmp/og118-chat-request.json"))
    try? JSONEncoder().encode(guardados.last!).write(to: URL(fileURLWithPath: "/tmp/og118-record-con-imagen.json"))
}

@MainActor
private func reintentarConservaLaImagen() async {
    print("reintentar un turno con foto la vuelve a mandar")
    var intentos = 0
    var imagenes: [[MessageImage]] = []
    let foto = MessageImage(mediaType: "image/jpeg", data: "/9j/4AAQ")
    let model = ChatModel(
        conversationID: "img-2",
        stream: { _, _, _, _, _, imgs in
            intentos += 1
            imagenes.append(imgs)
            return AsyncThrowingStream { c in
                if intentos == 1 { c.finish(throwing: Og118Error.badStatus(503)) } else {
                    c.yield(.text("listo")); c.yield(.done); c.finish()
                }
            }
        },
        restore: { _ in nil }
    )
    await model.restoreThread()
    model.send("mira", images: [foto])
    await settle()
    expect(model.reintentable != nil, "el 503 deja el turno reintentable")
    model.reintentar()
    await settle()
    expect(imagenes.last?.first?.data == foto.data, "y el reintento lleva la misma foto")
    expect(model.messages.filter { $0.role == .user }.count == 1, "sin duplicar la burbuja del usuario")
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
        await elModeloViajaDeIdaYVuelta()
        elCorreoSaleDelIdToken()
        imagenAdjuntaComoLaWeb()
        await adjuntosTopanEnCuatro()
        await laImagenViajaYSePersiste()
        await reintentarConservaLaImagen()
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
        await elArranqueEnFrioSeReintenta()
        elAutorSeLeeEnLasDosFormas()
        elAutorSeEscribeCanonico()
        guardarNoAmputaElRecordDeLaWeb()
        await cambiarDeChatNoArrastraElReintento()
        await elGuardBloqueaYSeVE()
        await cancelarElPlanNoEsCompletarlo()
        await elDesenlaceDelPlanLlega()
        await laEnmiendaViveEntreElAnuncioYElPlanNuevo()
        losFramesDelPlanYaNoSonBasura()
        resonanceElNucleoDeLaLlamada()
        await unaReaccionSolaEsRespuesta()
        await unTurnoDiferidoEsperaSinAcusarError()
        await laEsperaDiferidaNoEsEterna()
        await losVectoresDelTurnoSeCumplen()
        await losVectoresDeDerivacionesSeCumplen()
        await losVectoresDelHiloSeCumplen()
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
    let model = ChatModel(stream: { _, _, _, _, _, _ in
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

// MARK: - El autor: objeto canónico, no string

private func elAutorSeLeeEnLasDosFormas() {
    print("author: la forma canónica de la web Y el string viejo del iOS")
    let dec = JSONDecoder()

    // Lo que ESCRIBE LA WEB (MessageAuthor de free-intelligence-core). Esto es
    // lo que reventaba el hilo entero: «messages.Index 0.author» no es String.
    let web = """
    {"id":"c1","title":"t","createdAt":"2026-08-13T10:00:00Z","updatedAt":"2026-08-13T10:00:00Z",
     "messages":[{"role":"assistant","content":"hola","author":{"id":"53","name":"Yodo","symbol":"I"}}],
     "preview":"hola","schemaVersion":1}
    """.data(using: .utf8)!
    if let r = try? dec.decode(ConversationRecord.self, from: web) {
        expect(r.messages.count == 1, "el record de la web SÍ se decodifica")
        expect(r.messages.first?.author?.name == "Yodo", "y trae el nombre del autor")
        expect(r.messages.first?.author?.id == "53", "y su id, que es load-bearing")
        expect(r.chatMessages.count == 1, "el mensaje NO se descarta")
    } else {
        expect(false, "el record de la web SÍ se decodifica")
    }

    // Lo que el propio iOS ya escribió en la cuenta: un string suelto.
    let viejo = """
    {"id":"c2","title":"t","createdAt":"2026-08-13T10:00:00Z","updatedAt":"2026-08-13T10:00:00Z",
     "messages":[{"role":"assistant","content":"hola","author":"Yodo"}],
     "preview":"hola","schemaVersion":1}
    """.data(using: .utf8)!
    if let r = try? dec.decode(ConversationRecord.self, from: LegadoDeAutor.normalizar(viejo)) {
        expect(r.messages.first?.author?.name == "Yodo", "el string viejo del iOS sigue leyéndose")
        expect(r.chatMessages.count == 1, "y su mensaje tampoco se pierde")
    } else {
        expect(false, "el string viejo del iOS sigue leyéndose")
    }

    // Sin autor tampoco truena: los mensajes del usuario no lo llevan.
    let sinAutor = """
    {"id":"c3","title":"t","createdAt":"2026-08-13T10:00:00Z","updatedAt":"2026-08-13T10:00:00Z",
     "messages":[{"role":"user","content":"hola"}],"preview":"hola","schemaVersion":1}
    """.data(using: .utf8)!
    expect((try? dec.decode(ConversationRecord.self, from: sinAutor))?.chatMessages.count == 1,
           "un mensaje sin autor se lee igual")
}

private func elAutorSeEscribeCanonico() {
    print("author: el teléfono escribe lo que la web puede leer")
    let record = ConversationRecord.from(
        id: "c1",
        messages: [
            ChatMessage(role: .user, content: "hola"),
            ChatMessage(role: .assistant, content: "qué tal", author: ChatMessage.Autor(id: "53", nombre: "Yodo"))
        ],
        createdAt: "2026-08-13T10:00:00Z",
        now: "2026-08-13T10:00:01Z"
    )
    guard let datos = try? JSONEncoder().encode(record),
          let json = try? JSONSerialization.jsonObject(with: datos) as? [String: Any],
          let mensajes = json["messages"] as? [[String: Any]] else {
        expect(false, "el record se serializa")
        return
    }
    let autor = mensajes.last?["author"] as? [String: Any]
    expect(autor != nil, "el autor viaja como OBJETO, no como string")
    expect(autor?["id"] as? String == "53", "con su id")
    expect(autor?["name"] as? String == "Yodo", "y su nombre")
    expect(mensajes.first?["author"] == nil, "el mensaje del usuario no inventa autor")
}

// MARK: - Lo que el teléfono NO entiende no se borra

private func guardarNoAmputaElRecordDeLaWeb() {
    print("un turno desde el teléfono conserva imágenes y trace de la web")
    let dec = JSONDecoder()
    // Un record REAL de la web: el mensaje trae imágenes y trace, campos que
    // esta versión no modela. Antes se reescribía sin ellos y se perdían.
    let json = """
    {"id":"c1","title":"t","createdAt":"2026-08-13T10:00:00Z","updatedAt":"2026-08-13T10:00:00Z",
     "messages":[
       {"role":"user","content":"mira esta foto","images":[{"mediaType":"image/png","data":"QUJD"}]},
       {"role":"assistant","content":"la veo","author":{"id":"53","name":"Yodo"},
        "trace":{"steps":["mirar"]},"thinking":"pensando"}
     ],
     "preview":"la veo","schemaVersion":1}
    """.data(using: .utf8)!
    guard let base = try? dec.decode(ConversationRecord.self, from: json) else {
        expect(false, "el record de la web se decodifica"); return
    }

    // El teléfono contesta un turno más sobre ese hilo.
    var hilo = base.chatMessages
    hilo.append(ChatMessage(role: .user, content: "otra cosa"))
    hilo.append(ChatMessage(role: .assistant, content: "va", author: ChatMessage.Autor(id: "53", nombre: "Yodo")))
    let nuevo = ConversationRecord.from(
        id: "c1", messages: hilo,
        createdAt: base.createdAt, now: "2026-08-13T11:00:00Z", base: base
    )

    guard let datos = try? JSONEncoder().encode(nuevo),
          let raiz = try? JSONSerialization.jsonObject(with: datos) as? [String: Any],
          let msgs = raiz["messages"] as? [[String: Any]] else {
        expect(false, "el record se serializa"); return
    }
    expect(msgs.count == 4, "quedaron los 4 mensajes (fueron \(msgs.count))")
    let imagenes = msgs.first?["images"] as? [[String: Any]]
    expect(imagenes?.count == 1, "LA IMAGEN SOBREVIVE al turno del teléfono")
    expect(imagenes?.first?["data"] as? String == "QUJD", "y con sus bytes intactos")
    expect(msgs[1]["trace"] != nil, "el trace glass-box sobrevive")
    expect(msgs[1]["thinking"] as? String == "pensando", "y el thinking también")
    expect(msgs[3]["content"] as? String == "va", "el mensaje nuevo se escribe normal")
    expect((msgs[3]["author"] as? [String: Any])?["id"] as? String == "53", "con su autor canónico")
}

@MainActor
private func cambiarDeChatNoArrastraElReintento() async {
    print("el reintento de un chat NO puede dispararse en otro")
    // A: el turno truena. B: no existe en la cuenta. Antes, el botón de A
    // reaparecía sobre el error de B y mandaba el texto de A dentro de B.
    let model = ChatModel(
        stream: canned([]),
        restore: { _ in nil }
    )
    await model.restoreThread()
    model.send("mensaje de A")
    await settle()
    expect(model.reintentable == "mensaje de A", "A dejó su reintento pendiente")

    await model.open("otra-conversacion")
    await settle()
    expect(model.reintentable == nil, "abrir otro chat BORRA el reintento de A")
    expect(model.plan.vacio, "y el plan del turno anterior")
    expect(model.herramientas.isEmpty, "y sus herramientas")

    model.startNew()
    expect(model.reintentable == nil, "un chat nuevo tampoco lo hereda")
}

// MARK: - El ciclo de vida del plan (los 5 frames que llegaban como "sin mapear")

@MainActor
private func elGuardBloqueaYSeVE() async {
    print("un plan rechazado por el guard se pinta, no se traga")
    let model = ChatModel(stream: canned([
        .open,
        .plan(["Borrar la base", "Avisar"]),
        .planRejected(razon: "Un paso destruye datos", etiquetas: ["Borrar la base"], guardia: "no-destructivo"),
        .text("mejor no"), .done
    ]))
    model.send("x")
    await settle()
    expect(model.plan.rechazo?.razon == "Un paso destruye datos", "el motivo del rechazo llega")
    expect(model.plan.rechazo?.etiquetas == ["Borrar la base"], "y qué paso lo disparó")
    expect(model.plan.rechazo?.guardia == "no-destructivo", "y qué guardia fue")
    expect(model.plan.pasos.count == 2, "el plan NO se borra: el stream sigue y hay que verlo")
}

@MainActor
private func cancelarElPlanNoEsCompletarlo() async {
    print("plan_cancelled deja los pasos abiertos en CANCELADO, nunca en hecho")
    let model = ChatModel(stream: canned([
        .open,
        .plan(["Uno", "Dos", "Tres"]),
        .stepDone(index: 0, status: .done, summary: "listo", error: nil),
        .stepStarted(1),
        .planCancelled,
        .text("abandonado"), .done
    ]))
    model.send("x")
    await settle()
    let pasos = model.plan.pasos
    expect(pasos.first?.estado == .hecho, "un paso YA terminado conserva su estado")
    expect(pasos.count == 3 && pasos[1].estado == .cancelado, "el que corría queda CANCELADO, no hecho")
    expect(pasos.last?.estado == .cancelado, "y el que ni empezó, también")
    expect(model.plan.desenlace == .cancelado, "el plan queda marcado como cancelado")
}

@MainActor
private func elDesenlaceDelPlanLlega() async {
    print("plan_completed / plan_failed estampan el veredicto")
    let ok = ChatModel(stream: canned([
        .open, .plan(["a"]), .stepDone(index: 0, status: .done, summary: nil, error: nil),
        .planClosed(.completado), .text("ya"), .done
    ]))
    ok.send("x")
    await settle()
    expect(ok.plan.desenlace == .completado, "completado")
    expect(ok.plan.pasos.first?.estado == .hecho, "sin tocar el estado de los pasos")

    let mal = ChatModel(stream: canned([
        .open, .plan(["a"]), .stepDone(index: 0, status: .failed, summary: nil, error: "tronó"),
        .planClosed(.fallido), .text("ya"), .done
    ]))
    mal.send("x")
    await settle()
    expect(mal.plan.desenlace == .fallido, "fallido")
}

@MainActor
private func laEnmiendaViveEntreElAnuncioYElPlanNuevo() async {
    print("plan_amended es una insignia temporal, no un estado permanente")
    let model = ChatModel(stream: canned([
        .open, .plan(["viejo"]), .planAmended(.replanteado), .text("a"), .done
    ]))
    model.send("x")
    await settle()
    expect(model.plan.enmienda == .replanteado, "la insignia aparece con el anuncio")

    // El replan ANUNCIA y luego declara los pasos nuevos: ahí la insignia muere.
    let conPlanNuevo = ChatModel(stream: canned([
        .open, .plan(["viejo"]), .planAmended(.replanteado), .plan(["nuevo"]), .text("a"), .done
    ]))
    conPlanNuevo.send("x")
    await settle()
    expect(conPlanNuevo.plan.enmienda == nil, "el plan nuevo la limpia")
    expect(conPlanNuevo.plan.pasos.first?.etiqueta == "nuevo", "y trae los pasos nuevos")
}

private func losFramesDelPlanYaNoSonBasura() {
    print("los 5 frames del ciclo de vida SE MAPEAN, ya no caen en unmapped")
    let casos: [(String, Data)] = [
        ("plan_rejected", #"{"type":"plan_rejected","data":{"reason":"no"}}"#.data(using: .utf8)!),
        ("plan_amended", #"{"type":"plan_amended","data":{"action":"replan"}}"#.data(using: .utf8)!),
        ("plan_cancelled", #"{"type":"plan_cancelled","data":{}}"#.data(using: .utf8)!),
        ("plan_completed", #"{"type":"plan_completed","data":{}}"#.data(using: .utf8)!),
        ("plan_failed", #"{"type":"plan_failed","data":{}}"#.data(using: .utf8)!),
    ]
    for (nombre, datos) in casos {
        let evento = StreamEvent.decode(datos)
        var esBasura = false
        if case .unmapped = evento { esBasura = true }
        expect(evento != nil && !esBasura, "\(nombre) se mapea de verdad")
    }
}

// MARK: - El servidor dormido

private func elArranqueEnFrioSeReintenta() async {
    print("la primera petición despierta al servidor; la segunda es la buena")
    var intentos = 0
    let valor = try? await ArranqueEnFrio.conReintento { esReintento -> String in
        intentos += 1
        if !esReintento { throw URLError(.timedOut) }
        return "ok"
    }
    expect(intentos == 2, "hubo un reintento (hubo \(intentos))")
    expect(valor == "ok", "y el segundo intento entrega el dato")

    // Un fallo que no es de red no se reintenta: repetirlo daría el mismo
    // error y sólo retrasaría el mensaje al humano.
    var intentosAuth = 0
    let fallo = try? await ArranqueEnFrio.conReintento { _ -> String in
        intentosAuth += 1
        throw Og118Error.unauthorized
    }
    expect(intentosAuth == 1, "un 401 NO se reintenta (hubo \(intentosAuth))")
    expect(fallo == nil, "y el error sube")

    var intentosBuenos = 0
    let directo = try? await ArranqueEnFrio.conReintento { _ -> String in
        intentosBuenos += 1
        return "rápido"
    }
    expect(intentosBuenos == 1, "si responde a la primera no se repite")
    expect(directo == "rápido", "y devuelve lo suyo")

    expect(ArranqueEnFrio.esDeRed(URLError(.cannotConnectToHost)), "no conectar es de red")
    expect(ArranqueEnFrio.esDeRed(Og118Error.badStatus(500)) == false, "un 500 no es de red")
}

// MARK: - El parser contra BYTES REALES del servidor

private func elParserLeeUnTurnoDeVerdad() {
    print("SSEParser contra la captura real de /chat/stream")
    // Capturado con curl contra el server og118 corriendo local, mismo código
    // que el de Azure. Si el contrato del servidor cambia, esto se pone rojo
    // aquí y no en el teléfono de Bernard.
    let ruta = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("packages/free-intelligence-core/contracts/fixtures/turno-real.sse")
    guard let crudo = try? String(contentsOf: ruta, encoding: .utf8) else {
        expect(false, "la captura real existe en core/contracts/fixtures/turno-real.sse")
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
        case .result(let t, let m, _): resultado = t; modelo = m
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
    expect(model.errorMessage == Copy.turnEmpty, "el silencio se declara con la frase del contrato")
    expect(model.herramientas.contains("sin un solo frame"), "y la bitácora dice que no llegó un solo frame")
    expect(model.reintentable == "hola", "el mensaje queda listo para reintentar")
    expect(model.messages.isEmpty, "la burbuja optimista se revierte (hubo \(model.messages.count))")
    expect(model.borradorNoEnviado?.texto == "hola", "y el texto vuelve al composer")

    let conFrames = ChatModel(stream: canned([.open, .stepStarted(0), .done]))
    conFrames.send("hola")
    await settle()
    expect(conFrames.errorMessage == Copy.turnEmpty, "con frames pero sin texto, la misma frase")
    expect(conFrames.herramientas.contains("3 frames sin texto"), "y la bitácora dice cuántos llegaron")
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
    let model = ChatModel(stream: { _, _, history, _, _, _ in
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
    let model = ChatModel(stream: { _, _, _, _, _, _ in
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

// MARK: - Resonance: el núcleo de la llamada, mismo contrato que fi-glass

private func resonanceElNucleoDeLaLlamada() {
    print("resonance: máquina, efectos, cues, VAD y escala del analizador")
    let r = ResonanceMachine.reducir
    expect(r(.idle, .callStarted) == .listening, "llamar abre a escuchar")
    expect(r(.listening, .userSpeechEnded) == .transcribing, "fin de habla transcribe")
    expect(r(.transcribing, .sttCompleted) == .thinking, "la transcripción pasa a pensar")
    expect(r(.thinking, .assistantSpeechStarted) == .speaking, "la respuesta se habla")
    expect(r(.speaking, .assistantSpeechCompleted) == .silenceHold, "al terminar de hablar, silencio")
    expect(r(.silenceHold, .silenceResume) == .listening, "el auto-resume vuelve a escuchar")
    expect(r(.speaking, .userSpeechStarted) == .interrupted, "hablar encima interrumpe")
    expect(r(.thinking, .errorRecoverable) == .listening, "un fallo recuperable vuelve a escuchar")
    expect(r(.idle, .errorRecoverable) == .idle, "en reposo un fallo no arranca nada")
    expect(r(.transcribing, .errorFatal) == .ended, "un fallo fatal cuelga")
    expect(r(.ended, .callStarted) == .ended, "colgada es terminal")
    expect(r(.silenceHold, .userSpeechStarted) == .silenceHold, "en silencio la voz no cambia de estado, como la web")

    var efectos: [ResonanceEffect] = []
    let c = ResonanceController()
    c.alEfecto = { efectos.append($0) }
    c.empezarLlamada()
    c.enviar(.userSpeechEnded)
    c.sttCompleto("hola")
    c.respuestaLista("qué tal")
    c.interrumpir()
    expect(efectos == [.openMic, .beginTranscribe, .invokeAgent, .speak, .stopSpeaking, .openMic],
           "el turno completo despacha los efectos de la web en orden, con barge-in")
    expect(c.transcripcion == "hola" && c.textoAsistente == "qué tal", "guarda transcripción y respuesta")
    c.colgar()
    expect(c.estado == .ended && efectos.last == .endCall, "colgar despacha end_call")
    c.empezarLlamada()
    expect(c.estado == .listening, "una llamada nueva reinicia un controlador ya colgado")

    let p = ResonanceCuePolicy.acciones
    expect(p(.listening, .transcribing, .userSpeechEnded) == [.playLoop(.thinking), .playOnce(.crystalline)],
           "fin de habla: arranca el loop y suena el cristal")
    expect(p(.transcribing, .thinking, .sttCompleted) == [], "transcribir→pensar no reinicia el loop")
    expect(p(.thinking, .speaking, .assistantSpeechStarted) == [.stopLoop(.thinking)], "salir de pensar lo detiene")
    expect(p(.thinking, .listening, .errorRecoverable) == [.stopLoop(.thinking)], "un error tampoco lo deja colgado")
    expect(p(.speaking, .silenceHold, .assistantSpeechCompleted) == [.playOnce(.ready)], "al terminar suena «ready»")
    expect(p(.thinking, .ended, .callEnded) == [.stopAll], "colgar silencia todo")

    var g = ResonanceVadGate()
    expect(g.tick(nivel: 30, ahoraMs: 0, modo: .detect) == nil, "la voz no se declara antes de 180 ms")
    expect(g.tick(nivel: 30, ahoraMs: 180, modo: .detect) == .speechStart, "a los 180 ms sostenidos sí")
    expect(g.tick(nivel: 18, ahoraMs: 600, modo: .detect) == nil, "entre umbrales sigue siendo voz (histéresis)")
    expect(g.tick(nivel: 5, ahoraMs: 1000, modo: .detect) == nil, "silencio corto no cierra el turno")
    expect(g.tick(nivel: 5, ahoraMs: 1450, modo: .detect) == .speechEnd, "850 ms de silencio lo cierran")
    var largo = ResonanceVadGate()
    _ = largo.tick(nivel: 40, ahoraMs: 0, modo: .detect)
    _ = largo.tick(nivel: 40, ahoraMs: 200, modo: .detect)
    expect(largo.tick(nivel: 40, ahoraMs: 20_200, modo: .detect) == .speechEnd, "un turno se corta a los 20 s")
    var barge = ResonanceVadGate()
    _ = barge.tick(nivel: 30, ahoraMs: 0, modo: .barge)
    expect(barge.tick(nivel: 30, ahoraMs: 200, modo: .barge) == .bargeIn, "hablar encima del TTS dispara barge-in")
    expect(barge.tick(nivel: 30, ahoraMs: 400, modo: .barge) == nil, "una sola vez por interrupción")
    expect(ResonancePolicy.modoVad(.thinking) == .idle && ResonancePolicy.modoVad(.silenceHold) == .detect,
           "el modo del VAD sale del estado como en la web")

    var s = ResonanceSpectrum()
    let silencio = ResonanceSpectrum.nivel(s.bytes(Array(repeating: 0, count: 256)))
    expect(silencio == 0, "silencio digital = nivel 0, como getByteFrequencyData")
    // Fixture: AnalyserNode de Chrome (OfflineAudioContext 48 kHz, seno 1 kHz ×0.3, ganancia 2.5,
    // smoothing 0) leído en el frame 2560. El puerto debe dar los mismos bytes.
    let chrome: [UInt8] = [90, 93, 88, 195, 255, 255, 255, 255, 139, 90, 81, 67, 53, 40, 29, 19, 10, 1]
        + [UInt8](repeating: 0, count: 110)
    var exacto = ResonanceSpectrum(smoothing: 0)
    let tono = (2304..<2560).map { Float(0.3 * sin(2 * Double.pi * 1000 * Double($0) / 48_000)) * ResonancePolicy.gain }
    let propios = exacto.bytes(tono)
    let peor = zip(propios, chrome).map { abs(Int($0) - Int($1)) }.max() ?? 255
    expect(peor <= 1, "los 128 bins coinciden con el AnalyserNode de Chrome (peor diferencia \(peor))")
    var semilla: UInt64 = 7
    let vozAncha = (0..<256).map { _ -> Float in
        semilla = semilla &* 6364136223846793005 &+ 1442695040888963407
        return (Float(semilla >> 40) / Float(1 << 24) * 2 - 1) * 0.05 * ResonancePolicy.gain
    }
    var ancha = ResonanceSpectrum()
    var nivelVoz = 0.0
    for _ in 0..<20 { nivelVoz = ResonanceSpectrum.nivel(ancha.bytes(vozAncha)) }
    expect(nivelVoz > 24, "una señal de banda ancha a 0.05 cruza el umbral de 24 (midió \(Int(nivelVoz)); Chrome mide 166)")
    var debil = ResonanceSpectrum()
    let ruido = (0..<256).map { Float(0.0002 * sin(2 * Double.pi * 300 * Double($0) / 48_000)) * ResonancePolicy.gain }
    var nivelRuido = 0.0
    for _ in 0..<20 { nivelRuido = ResonanceSpectrum.nivel(debil.bytes(ruido)) }
    expect(nivelRuido < 13, "un murmullo de fondo queda bajo el piso de 13 (midió \(Int(nivelRuido)))")
    expect(ResonanceSpectrum.bandas([UInt8](repeating: 255, count: 128), cuantas: 24, ganancia: 2.5).allSatisfy { $0 == 1 },
           "las bandas se recortan a 1")
    expect(ResonancePolicy.etiqueta(.speaking, oyendo: false) == "Hablando — puedes interrumpir"
           && ResonancePolicy.etiqueta(.listening, oyendo: true) == "Te oigo", "las etiquetas son las de la web")
}

// MARK: - reactions: el campo del contrato que el teléfono no veía

@MainActor
private func unaReaccionSolaEsRespuesta() async {
    print("un turno con reacción y sin texto es una respuesta, no un error")
    var guardados: [ConversationRecord] = []
    let model = ChatModel(
        stream: canned([.open, .result(text: "", model: nil, reactions: ["🔥", "👀"]), .done]),
        persist: { guardados.append($0) },
        restore: { _ in nil }
    )
    await model.restoreThread()
    model.send("mira esto")
    await settle()

    expect(model.errorMessage == nil, "no acusa 'frames sin texto'")
    expect(model.reintentable == nil, "ni ofrece reintentar")
    expect(model.messages.count == 2, "la reacción deja su burbuja (hubo \(model.messages.count))")
    expect(model.messages.last?.reactions == ["🔥", "👀"], "con las reacciones del contrato")
    expect(model.messages.last?.content == "", "y sin inventar texto")
    guard let r = guardados.last else { return expect(false, "se guardó el turno") }
    expect(r.messages.last?.reactions == ["🔥", "👀"], "y se persisten donde la web las lee")
    let releido = try? JSONDecoder().decode(ConversationRecord.self, from: JSONEncoder().encode(r))
    expect(releido?.chatMessages.last?.reactions == ["🔥", "👀"], "y vuelven al reabrir el hilo")
}

// MARK: - deferred: el frame que rompió la compilación en main sin que nadie lo viera

@MainActor
private func unTurnoDiferidoEsperaSinAcusarError() async {
    print("deferred: el motor sigue trabajando, no es un error, y la respuesta llega al hilo")
    var tardio: ConversationRecord?
    let model = ChatModel(
        conversationID: "abc-123",
        stream: canned([.open, .author(id: "53", name: "Yodo"), .deferred, .done]),
        persist: { _ in },
        restore: { _ in tardio },
        now: { "2026-10-17T12:00:00Z" },
        pausa: { try? await Task.sleep(nanoseconds: 20_000_000) }
    )
    await model.restoreThread()
    model.send("¿y entonces?")
    await settle()

    expect(model.errorMessage == nil, "no acusa error")
    expect(model.reintentable == nil, "no ofrece reintentar: no hay nada que rehacer")
    expect(model.messages.count == 1, "no inventa una burbuja vacía (hubo \(model.messages.count))")
    expect(
        model.avisoDeEspera == "Yodo sigue escribiendo. Su respuesta aparecerá aquí en cuanto termine.",
        "avisa con la frase de core, con el autor del turno (\(model.avisoDeEspera ?? "nil"))"
    )

    tardio = ConversationRecord.from(
        id: "abc-123",
        messages: [
            ChatMessage(role: .user, content: "¿y entonces?"),
            ChatMessage(role: .assistant, content: "llegué tarde", author: ChatMessage.Autor(id: "53", nombre: "Yodo"))
        ],
        createdAt: "2026-10-17T12:00:00Z",
        now: "2026-10-17T12:00:09Z"
    )
    await settle()
    expect(model.messages.count == 2, "la respuesta tardía entra al hilo (hubo \(model.messages.count))")
    expect(model.messages.last?.content == "llegué tarde", "con el texto que el servidor guardó")
    expect(model.avisoDeEspera == nil, "y el aviso se apaga solo")
}

@MainActor
private func laEsperaDiferidaNoEsEterna() async {
    print("deferred: si la respuesta nunca llega, el aviso lo dice en vez de mentir 'sigue escribiendo'")
    let model = ChatModel(
        conversationID: "abc-123",
        stream: canned([.open, .deferred, .done]),
        persist: { _ in },
        restore: { _ in nil },
        pausa: {}
    )
    await model.restoreThread()
    model.send("¿y entonces?")
    await settle()
    expect(model.avisoDeEspera == Copy.turnDeferredTimeout,
           "tras agotar los reintentos el aviso cambia (\(model.avisoDeEspera ?? "nil"))")
    expect(model.errorMessage == nil, "y sigue sin ser un error")
}

// MARK: - contracts/agent-turn.vectors.json — la máquina del turno como contrato

private func canonico(_ objeto: Any) -> String {
    guard let datos = try? JSONSerialization.data(withJSONObject: objeto, options: [.sortedKeys, .fragmentsAllowed]) else {
        return "<no-json>"
    }
    return String(decoding: datos, as: UTF8.self)
}

@MainActor
private func proyeccionDelTurno(_ model: ChatModel) -> [String: Any] {
    let ultimo = model.messages.last(where: { $0.role == .assistant })
    let p = model.plan
    var plan: Any = NSNull()
    if !(p.vacio && p.rechazo == nil && p.enmienda == nil && p.desenlace == nil) {
        let pasos: [[String: Any]] = p.pasos.map { paso in
            let estado: String = switch paso.estado {
            case .pendiente: "pending"
            case .corriendo: "running"
            case .hecho: "done"
            case .fallido: "failed"
            case .cancelado: "cancelled"
            }
            let detalle: Any = paso.detalle ?? NSNull()
            return [
                "label": paso.etiqueta,
                "status": estado,
                "summary": paso.estado == .hecho ? detalle : NSNull(),
                "error": paso.estado == .hecho ? NSNull() : detalle,
                "note": paso.nota ?? NSNull()
            ]
        }
        let rechazo: Any = p.rechazo.map {
            ["reason": $0.razon, "matched": $0.etiquetas, "guard": $0.guardia ?? NSNull()] as [String: Any]
        } ?? NSNull()
        let desenlace: Any = p.desenlace.map { d -> String in
            switch d {
            case .completado: "completed"
            case .fallido: "failed"
            case .cancelado: "cancelled"
            }
        } ?? NSNull()
        plan = [
            "steps": pasos,
            "rejection": rechazo,
            "amended": p.enmienda?.rawValue ?? NSNull(),
            "outcome": desenlace
        ] as [String: Any]
    }
    return [
        "text": model.textoDelUltimoTurno,
        "status": model.errorMessage == nil ? "done" : "error",
        "deferred": model.avisoDeEspera != nil,
        "reactions": ultimo?.reactions ?? [],
        "author": ultimo?.author.map { ["id": $0.id, "name": $0.nombre] as [String: Any] } ?? NSNull(),
        "plan": plan
    ]
}

@MainActor
private func losVectoresDelTurnoSeCumplen() async {
    print("agent-turn.vectors.json: la máquina del turno obedece el mismo contrato que core")
    let ruta = URL(fileURLWithPath: #filePath).absoluteURL
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("packages/free-intelligence-core/contracts/agent-turn.vectors.json")
    guard let datos = try? Data(contentsOf: ruta),
          let raiz = try? JSONSerialization.jsonObject(with: datos) as? [String: Any],
          let vectores = raiz["vectors"] as? [[String: Any]], !vectores.isEmpty else {
        expect(false, "el contrato existe y trae vectores: \(ruta.path)")
        return
    }
    for vector in vectores {
        let nombre = vector["name"] as? String ?? "?"
        let frames = vector["events"] as? [[String: Any]] ?? []
        let eventos = frames.compactMap { frame -> StreamEvent? in
            guard let d = try? JSONSerialization.data(withJSONObject: frame) else { return nil }
            return StreamEvent.decode(d)
        }
        let model = ChatModel(stream: canned(eventos))
        model.send("vector")
        await settle()
        let actual = canonico(proyeccionDelTurno(model))
        let esperado = canonico(vector["expect"] ?? NSNull())
        expect(actual == esperado, "\(nombre)\n       esperado \(esperado)\n       actual   \(actual)")
    }
}

// MARK: - contracts/conversation-derivations.vectors.json

private func contrato(_ nombre: String) -> [[String: Any]]? {
    let ruta = URL(fileURLWithPath: #filePath).absoluteURL
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .appendingPathComponent("packages/free-intelligence-core/contracts/\(nombre)")
    guard let datos = try? Data(contentsOf: ruta),
          let raiz = try? JSONSerialization.jsonObject(with: datos) as? [String: Any],
          let vectores = raiz["vectors"] as? [[String: Any]], !vectores.isEmpty else {
        expect(false, "el contrato existe y trae vectores: \(ruta.path)")
        return nil
    }
    return vectores
}

private func mensajes(_ crudos: Any?) -> [ChatMessage] {
    (crudos as? [[String: Any]] ?? []).compactMap { m in
        guard let rol = ChatMessage.Role(rawValue: m["role"] as? String ?? "") else { return nil }
        return ChatMessage(role: rol, content: m["content"] as? String ?? "")
    }
}

@MainActor
private func losVectoresDeDerivacionesSeCumplen() async {
    print("conversation-derivations.vectors.json: título, preview, rename y sidebar como en core")
    guard let vectores = contrato("conversation-derivations.vectors.json") else { return }
    for vector in vectores {
        let nombre = vector["name"] as? String ?? "?"
        let entrada = vector["input"] as? [String: Any] ?? [:]
        var actual: Any = NSNull()
        switch vector["kind"] as? String {
        case "title":
            actual = ConversationSchema.title(mensajes(entrada["messages"]))
        case "preview":
            actual = ConversationSchema.preview(mensajes(entrada["messages"]))
        case "rename":
            let base = entrada["record"] as? [String: Any] ?? [:]
            var record = ConversationRecord.from(
                id: "c", messages: mensajes(base["messages"]), createdAt: "2026-10-17T00:00:00Z", now: "2026-10-17T00:00:00Z"
            )
            record.title = base["title"] as? String ?? record.title
            record.titleCustom = (base["titleCustom"] as? Bool) == true ? true : nil
            let r = record
            let modelo = ConversationsModel(list: { [] }, load: { _ in r }, save: { _ in })
            let guardado = await modelo.rename("c", to: entrada["newTitle"] as? String ?? "")
            actual = ["title": guardado?.title ?? "", "titleCustom": guardado?.titleCustom == true] as [String: Any]
        case "organize":
            let datos = (try? JSONSerialization.data(withJSONObject: entrada["summaries"] ?? [])) ?? Data()
            let lista = (try? JSONDecoder().decode([ConversationSummary].self, from: datos)) ?? []
            let modelo = ConversationsModel(list: { lista })
            await modelo.refresh()
            actual = [
                "pinned": modelo.pinned.map(\.id),
                "active": modelo.active.map(\.id),
                "archived": modelo.archived.map(\.id)
            ] as [String: Any]
        default:
            break
        }
        let esperado = canonico(vector["expect"] ?? NSNull())
        let visto = canonico(actual)
        expect(visto == esperado, "\(nombre)\n       esperado \(esperado)\n       actual   \(visto)")
    }
}

// MARK: - contracts/conversation-state.vectors.json

private func eventosDeDesenlace(_ op: [String: Any]) -> [StreamEvent] {
    let texto = op["text"] as? String ?? ""
    let reacciones = op["reactions"] as? [String] ?? []
    var eventos: [StreamEvent] = [.open]
    if !texto.isEmpty { eventos.append(.text(texto)) }
    if !reacciones.isEmpty { eventos.append(.result(text: "", model: nil, reactions: reacciones)) }
    if op["deferred"] as? Bool == true { eventos.append(.deferred) }
    eventos.append(.done)
    return eventos
}

/// Cómo termina el stream de un vector: con frames, tronando el transporte, o
/// colgado hasta que el usuario lo para (`stopped`).
private enum DesenlaceDelTurno {
    case eventos([StreamEvent])
    case falla
    case colgado
}

/// Sin texto parcial la falla es un transporte que truena; con texto parcial es
/// un frame `error` a mitad del turno, que también revierte.
private func desenlace(_ op: [String: Any], falla: Bool) -> DesenlaceDelTurno {
    if op["stopped"] as? Bool == true { return .colgado }
    guard falla else { return .eventos(eventosDeDesenlace(op)) }
    guard let parcial = op["partialText"] as? String, !parcial.isEmpty else { return .falla }
    return .eventos([.open, .text(parcial), .failure(op["message"] as? String ?? "error"), .done])
}

@MainActor
private func proyeccionDelHilo(_ model: ChatModel) -> [String: Any] {
    [
        "messages": model.messages.map { ["role": $0.role.rawValue, "content": $0.content] as [String: Any] },
        "failure": model.errorMessage == nil ? NSNull() : (model.tipoDeFalla == .vacio ? "empty" : "stream"),
        "unsentText": model.borradorNoEnviado?.texto ?? NSNull(),
        "lastSentText": model.ultimoEnvio?.texto ?? NSNull()
    ]
}

@MainActor
private func losVectoresDelHiloSeCumplen() async {
    print("conversation-state.vectors.json: envío, fold, falla, reintento e hidratación como en core")
    guard let vectores = contrato("conversation-state.vectors.json") else { return }
    for vector in vectores {
        let nombre = vector["name"] as? String ?? "?"
        let ops = vector["ops"] as? [[String: Any]] ?? []
        var cola: [DesenlaceDelTurno] = []
        let stream: ChatModel.Stream = { _, _, _, _, _, _ in
            let siguiente: DesenlaceDelTurno = cola.isEmpty ? .eventos([]) : cola.removeFirst()
            return AsyncThrowingStream { c in
                switch siguiente {
                case .falla:
                    c.finish(throwing: Og118Error.unauthorized)
                case .colgado:
                    c.yield(.open)
                case .eventos(let eventos):
                    for e in eventos { c.yield(e) }
                    c.finish()
                }
            }
        }
        var semilla: ConversationRecord?
        if let primero = ops.first, primero["op"] as? String == "hydrate" {
            semilla = ConversationRecord.from(
                id: "v", messages: mensajes(primero["messages"]), createdAt: "2026-10-17T00:00:00Z", now: "2026-10-17T00:00:00Z"
            )
        }
        let registro = semilla
        let model = ChatModel(
            conversationID: "v",
            stream: stream,
            persist: { _ in },
            restore: { _ in registro },
            pausa: {}
        )
        await model.restoreThread()
        var i = 0
        while i < ops.count {
            let op = ops[i]
            switch op["op"] as? String ?? "" {
            case "send", "retry":
                var parado = false
                if i + 1 < ops.count, let sig = ops[i + 1]["op"] as? String, sig == "settled" || sig == "failed" {
                    parado = ops[i + 1]["stopped"] as? Bool == true
                    cola.append(desenlace(ops[i + 1], falla: sig == "failed"))
                    i += 1
                } else {
                    cola.append(.eventos([]))
                }
                if op["op"] as? String == "send" {
                    model.send(op["text"] as? String ?? "")
                } else {
                    model.reintentar()
                }
                await settle()
                if parado {
                    model.cancel()
                    await settle()
                }
            case "dismiss_failure":
                model.errorMessage = nil
            case "clear_unsent":
                model.borradorRestaurado()
            default:
                break
            }
            i += 1
        }
        let esperado = canonico(vector["expect"] ?? NSNull())
        let visto = canonico(proyeccionDelHilo(model))
        expect(visto == esperado, "\(nombre)\n       esperado \(esperado)\n       actual   \(visto)")
    }
}
