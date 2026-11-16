import Foundation

func cacheTemporal() -> CacheLocal {
    CacheLocal(carpeta: FileManager.default.temporaryDirectory.appendingPathComponent("og118-harness-\(UUID().uuidString)"))
}

func recordDePrueba(_ contenidos: [String]) -> ConversationRecord {
    ConversationRecord.from(
        id: "abc-123",
        messages: contenidos.enumerated().map { ChatMessage(role: $0.offset % 2 == 0 ? .user : .assistant, content: $0.element) },
        createdAt: "2026-11-15T12:00:00Z",
        now: "2026-11-15T12:00:30Z"
    )
}

@MainActor
func sinRedElHiloSeLeeDeLaCache() async {
    print("sin red, el hilo se pinta de lo guardado en disco y no deja escribir encima")
    let cache = cacheTemporal()
    defer { cache.vaciar() }
    cache.guardar(recordDePrueba(["hola", "qué onda"]))
    let model = ChatModel(
        conversationID: "abc-123",
        stream: canned([]),
        persist: { _ in },
        restore: { _ in throw URLError(.notConnectedToInternet) },
        cache: cache
    )
    await model.restoreThread()
    expect(model.messages.count == 2, "el hilo guardado se ve (hubo \(model.messages.count))")
    expect(model.cargaFallida != nil, "y se dice que el servidor no contestó")
    expect(model.hiloListo == false, "no se puede mandar sobre un hilo sin confirmar")

    let borrado = ChatModel(
        conversationID: "abc-123",
        stream: canned([]),
        persist: { _ in },
        restore: { _ in nil },
        cache: cache
    )
    await borrado.restoreThread()
    expect(borrado.messages.isEmpty, "un hilo que el servidor ya no tiene no revive de la caché")
    expect(cache.hilo("abc-123") == nil, "y se borra del disco")

    cache.guardarLista([])
    expect(cache.lista().isEmpty, "la lista vacía se guarda y se lee")
}

@MainActor
func unGuardadoQueNoLlegoSeVuelveASubir() async {
    print("un guardado que no llegó queda marcado y se sube en el siguiente arranque")
    let cache = cacheTemporal()
    defer { cache.vaciar() }
    var fallar = true
    var subidos: [ConversationRecord] = []
    let model = ChatModel(
        conversationID: "abc-123",
        stream: canned([.open, .text("respuesta"), .done]),
        persist: { record in
            if fallar { throw URLError(.networkConnectionLost) }
            subidos.append(record)
        },
        restore: { _ in subidos.last },
        cache: cache,
        pausa: { try? await Task.sleep(nanoseconds: 3_000_000_000) }
    )
    await model.restoreThread()
    model.send("pregunta")
    await settle()
    expect(cache.estaPendiente("abc-123"), "el guardado fallido queda marcado en disco")
    expect(cache.hilo("abc-123")?.messages.count == 2, "con el turno completo")

    fallar = false
    let siguiente = ChatModel(
        conversationID: "abc-123",
        stream: canned([]),
        persist: { subidos.append($0) },
        restore: { _ in nil },
        cache: cache
    )
    await siguiente.restoreThread()
    await esperar { !subidos.isEmpty }
    expect(siguiente.messages.count == 2, "el arranque siguiente pinta el turno que no subió")
    expect(subidos.last?.messages.count == 2, "y lo sube (subidos: \(subidos.count))")
    await esperar { !cache.estaPendiente("abc-123") }
    expect(cache.estaPendiente("abc-123") == false, "al llegar, la marca se quita")
}

func elBorradorSobreviveYSeLimpia() {
    print("el borrador de cada conversación sobrevive y cerrar sesión los borra todos")
    let defaults = UserDefaults(suiteName: "og118-harness-\(UUID().uuidString)")!
    BorradorStore.guardar("a medias", "abc", defaults: defaults)
    BorradorStore.guardar("otro", "xyz", defaults: defaults)
    expect(BorradorStore.leer("abc", defaults: defaults) == "a medias", "se lee por conversación")
    BorradorStore.guardar("", "abc", defaults: defaults)
    expect(BorradorStore.leer("abc", defaults: defaults).isEmpty, "mandar el mensaje lo borra")
    BorradorStore.vaciar(defaults: defaults)
    expect(BorradorStore.leer("xyz", defaults: defaults).isEmpty, "cerrar sesión no deja ninguno")
}
