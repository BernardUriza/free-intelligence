import Foundation

// MARK: - El turno que muere en silencio

@MainActor
func elTurnoVacioSeDeclara() async {
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
func elTurnoBuenoNoOfreceReintento() async {
    print("un turno que sí contesta no ensucia la pantalla")
    let model = ChatModel(stream: canned([.open, .text("hola"), .done]))
    model.send("x")
    await settle()
    expect(model.errorMessage == nil, "sin error")
    expect(model.reintentable == nil, "sin botón de reintentar")
}

@MainActor
func reintentarNoDuplicaLaBurbujaDelUsuario() async {
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
func cancelarNoOfreceReintento() async {
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

// MARK: - reactions: el campo del contrato que el teléfono no veía

@MainActor
func unaReaccionSolaEsRespuesta() async {
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
func unTurnoDiferidoEsperaSinAcusarError() async {
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
    await esperar { model.messages.count == 2 && model.avisoDeEspera == nil }
    expect(model.messages.count == 2, "la respuesta tardía entra al hilo (hubo \(model.messages.count))")
    expect(model.messages.last?.content == "llegué tarde", "con el texto que el servidor guardó")
    expect(model.avisoDeEspera == nil, "y el aviso se apaga solo")
}

@MainActor
func elModeloAvisaCadaRespuestaQueEntra() async {
    print("el modelo avisa cuando entra una respuesta, viva o tardía, y calla cuando el turno falla")
    var avisos: [(String, String)] = []
    let vivo = ChatModel(conversationID: "abc-123", stream: canned([.open, .text("hola"), .done]))
    vivo.alRecibirRespuesta = { avisos.append(($0.content, $1)) }
    vivo.send("uno")
    await settle()
    expect(avisos.count == 1 && avisos.first?.0 == "hola" && avisos.first?.1 == "abc-123", "un turno que contesta avisa una vez, con su hilo (\(avisos.count))")

    var fallidos = 0
    let roto = ChatModel(conversationID: "abc-123", stream: cortado([]))
    roto.alRecibirRespuesta = { _, _ in fallidos += 1 }
    roto.send("dos")
    await settle()
    expect(fallidos == 0, "un turno que falla no avisa nada")

    var tardios: [String] = []
    var servidor: ConversationRecord?
    let diferido = ChatModel(
        conversationID: "abc-123",
        stream: cortado([.open]),
        persist: { _ in },
        restore: { _ in servidor },
        pausa: { try? await Task.sleep(nanoseconds: 20_000_000) }
    )
    diferido.alRecibirRespuesta = { respuesta, _ in tardios.append(respuesta.content) }
    await diferido.restoreThread()
    diferido.send("tres")
    await settle()
    expect(tardios.isEmpty, "mientras la respuesta no llega, no hay aviso")
    servidor = recordDePrueba(["tres", "llegó tarde"])
    await esperar { !tardios.isEmpty }
    expect(tardios == ["llegó tarde"], "la respuesta que aterriza tarde también avisa (\(tardios))")
}

func cortado(_ antes: [StreamEvent]) -> ChatModel.Stream {
    { _, _, _, _, _, _ in
        AsyncThrowingStream { continuation in
            for event in antes { continuation.yield(event) }
            continuation.finish(throwing: URLError(.networkConnectionLost))
        }
    }
}

@MainActor
func unaConexionCaidaNoRevierteElTurnoQueElServidorYaAbrio() async {
    print("cambiar de app a medio turno: el turno termina en el servidor y la respuesta llega sola")
    var tardio: ConversationRecord?
    let model = ChatModel(
        conversationID: "abc-123",
        stream: cortado([.open, .author(id: "53", name: "Yodo"), .text("a medias")]),
        persist: { _ in },
        restore: { _ in tardio },
        now: { "2026-11-15T12:00:00Z" },
        pausa: { try? await Task.sleep(nanoseconds: 20_000_000) }
    )
    await model.restoreThread()
    model.send("¿sigues ahí?")
    await settle()

    expect(model.errorMessage == nil, "una conexión caída con el turno abierto no es un error")
    expect(model.reintentable == nil, "no ofrece reintentar: reintentar lo cobraría dos veces")
    expect(model.borradorNoEnviado == nil, "el mensaje no regresa al composer")
    expect(model.messages.count == 1 && model.messages.first?.role == .user, "la pregunta se queda y el texto a medias no se guarda (hubo \(model.messages.count))")
    expect(model.avisoDeEspera != nil, "avisa que la respuesta viene en camino")

    tardio = ConversationRecord.from(
        id: "abc-123",
        messages: [
            ChatMessage(role: .user, content: "¿sigues ahí?"),
            ChatMessage(role: .assistant, content: "aquí sigo, completa")
        ],
        createdAt: "2026-11-15T12:00:00Z",
        now: "2026-11-15T12:00:30Z"
    )
    await esperar { model.messages.count == 2 }
    expect(model.messages.last?.content == "aquí sigo, completa", "entra la respuesta completa que el servidor guardó")
    expect(model.avisoDeEspera == nil, "y el aviso se apaga")
}

@MainActor
func sinUnSoloFrameElTurnoSiSeRevierte() async {
    print("si la petición nunca llegó al servidor, el mensaje vuelve al composer como siempre")
    let model = ChatModel(
        conversationID: "abc-123",
        stream: cortado([]),
        persist: { _ in },
        restore: { _ in nil },
        pausa: { try? await Task.sleep(nanoseconds: 20_000_000) }
    )
    await model.restoreThread()
    model.send("hola")
    await settle()
    expect(model.errorMessage != nil, "hay error visible")
    expect(model.reintentable == "hola", "y se puede reintentar")
    expect(model.messages.isEmpty, "la burbuja se revierte")
}

@MainActor
func pararAvisaAlServidorYVolverResincroniza() async {
    print("parar a mano cancela el turno en el servidor; volver a la app trae lo que se escribió allá")
    var detenidos: [String] = []
    var servidor: ConversationRecord?
    let model = ChatModel(
        conversationID: "abc-123",
        stream: { _, _, _, _, _, _ in AsyncThrowingStream { $0.yield(.open) } },
        persist: { _ in },
        restore: { _ in servidor },
        detener: { detenidos.append($0) },
        pausa: { try? await Task.sleep(nanoseconds: 20_000_000) }
    )
    await model.restoreThread()
    model.send("uno")
    await settle()
    model.cancel()
    await settle()
    expect(detenidos == ["abc-123"], "el servidor se entera de que se paró (\(detenidos))")
    expect(model.avisoDeEspera == nil, "y no se queda esperando una respuesta")

    servidor = ConversationRecord.from(
        id: "abc-123",
        messages: [
            ChatMessage(role: .user, content: "uno"),
            ChatMessage(role: .assistant, content: "desde otro lado"),
            ChatMessage(role: .user, content: "dos")
        ],
        createdAt: "2026-11-15T12:00:00Z",
        now: "2026-11-15T12:01:00Z"
    )
    await model.resincronizar()
    expect(model.messages.count == 3, "al volver entra lo que el servidor tiene de más (hubo \(model.messages.count))")
}

@MainActor
func laEsperaDiferidaNoEsEterna() async {
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
