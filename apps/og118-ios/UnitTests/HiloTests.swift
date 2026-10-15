import Foundation
import Testing
@testable import og118

/// Un stream que contesta de inmediato con un texto fijo.
private func stream(_ texto: String) -> ChatModel.Stream {
    { _, _, _, _, _, _ in
        AsyncThrowingStream { c in
            c.yield(.text(texto))
            c.yield(.done)
            c.finish()
        }
    }
}

private func record(_ id: String, mensajes: [(PersistedMessageRole, String)], pinnedAt: String? = nil, title: String? = nil) -> ConversationRecord {
    ConversationRecord(
        id: id,
        title: title ?? "t",
        titleCustom: title == nil ? nil : true,
        createdAt: "2026-10-01T00:00:00Z",
        updatedAt: "2026-10-01T00:00:00Z",
        messages: mensajes.map { PersistedMessage(role: $0.0, content: $0.1, timestamp: nil, author: nil, images: nil, trace: nil) },
        preview: "",
        pinnedAt: pinnedAt,
        archivedAt: nil,
        schemaVersion: 1
    )
}

@MainActor
private func esperar(_ condicion: @MainActor () -> Bool) async {
    var vueltas = 0
    while !condicion() && vueltas < 20_000 {
        vueltas += 1
        await Task.yield()
    }
}

private func defaults() -> UserDefaults {
    let d = UserDefaults(suiteName: "hilo-tests-\(UUID().uuidString)")!
    return d
}

@MainActor
@Test func unRestoreFallidoNoDejaEnviarNiEscribeEnElServidor() async {
    var puts = 0
    let chat = ChatModel(
        conversationID: "c1",
        stream: stream("hola"),
        persist: { _ in puts += 1 },
        restore: { _ in throw URLError(.timedOut) },
        defaults: defaults()
    )
    await chat.restoreThread()
    #expect(!chat.hiloListo)
    #expect(chat.cargaFallida != nil)

    chat.send("esto no debe salir")
    #expect(!chat.isStreaming)
    #expect(chat.messages.isEmpty)
    await esperar { false }
    #expect(puts == 0)
}

@MainActor
@Test func reintentarCargaDesbloqueaElHilo() async {
    var intentos = 0
    let base = record("c2", mensajes: [(.user, "antes"), (.assistant, "sí")])
    let chat = ChatModel(
        conversationID: "c2",
        stream: stream("hola"),
        persist: { _ in },
        restore: { _ in
            intentos += 1
            if intentos == 1 { throw URLError(.networkConnectionLost) }
            return base
        },
        defaults: defaults()
    )
    await chat.restoreThread(esperabaRecord: true)
    #expect(chat.cargaFallida != nil)
    chat.reintentarCarga()
    await esperar { chat.hiloListo }
    #expect(chat.cargaFallida == nil)
    #expect(chat.messages.count == 2)
}

@MainActor
@Test func abrirElMismoChatTrasUnaFallaReintentaLaCarga() async {
    var intentos = 0
    let chat = ChatModel(
        conversationID: "c0",
        stream: stream("x"),
        persist: { _ in },
        restore: { id in
            intentos += 1
            if intentos == 1 { throw URLError(.timedOut) }
            return record(id, mensajes: [(.user, "q"), (.assistant, "r")])
        },
        defaults: defaults()
    )
    await chat.open("c3")
    #expect(!chat.hiloListo)
    await chat.open("c3")
    #expect(chat.hiloListo)
    #expect(chat.messages.count == 2)
    #expect(intentos == 2)
}

@MainActor
@Test func unChatQueLaListaMostroYNoEstaEsFallaNoHiloNuevo() async {
    var puts = 0
    let chat = ChatModel(
        conversationID: "c0",
        stream: stream("x"),
        persist: { _ in puts += 1 },
        restore: { _ in nil },
        defaults: defaults()
    )
    await chat.open("borrado-en-la-web")
    #expect(!chat.hiloListo)
    #expect(chat.cargaFallida == "Esta conversación no está en tu cuenta.")
    chat.send("hola")
    await esperar { false }
    #expect(puts == 0)
}

@MainActor
@Test func elPutConservaLoQueOtroClienteAgregoYSuPin() async {
    let base = record("c4", mensajes: [(.user, "a"), (.assistant, "b")])
    var vivo = base
    var guardados: [ConversationRecord] = []
    var lecturas = 0
    let chat = ChatModel(
        conversationID: "c4",
        stream: stream("respuesta"),
        persist: { guardados.append($0) },
        restore: { _ in
            lecturas += 1
            return vivo
        },
        defaults: defaults()
    )
    await chat.restoreThread()
    #expect(chat.messages.count == 2)

    vivo = record(
        "c4",
        mensajes: [(.user, "a"), (.assistant, "b"), (.assistant, "lo agregó la web")],
        pinnedAt: "2026-10-15T00:00:00Z",
        title: "Renombrado en la web"
    )
    chat.send("pregunta")
    await esperar { !guardados.isEmpty }

    let put = guardados[0]
    #expect(put.messages.map(\.content) == ["a", "b", "lo agregó la web", "pregunta", "respuesta"])
    #expect(put.pinnedAt == "2026-10-15T00:00:00Z")
    #expect(put.title == "Renombrado en la web")
    #expect(chat.messages.map(\.content) == ["a", "b", "lo agregó la web", "pregunta", "respuesta"])
    #expect(lecturas == 2)
}

@MainActor
@Test func sinRecordVivoElPutEsElDeSiempre() async {
    var guardados: [ConversationRecord] = []
    let chat = ChatModel(
        conversationID: "c5",
        stream: stream("r"),
        persist: { guardados.append($0) },
        restore: { _ in nil },
        defaults: defaults()
    )
    await chat.restoreThread()
    chat.send("q")
    await esperar { !guardados.isEmpty }
    #expect(guardados[0].messages.map(\.content) == ["q", "r"])
    #expect(guardados[0].title == "q")
}
