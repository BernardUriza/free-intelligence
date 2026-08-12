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

@main
struct Harness {
    static func main() async {
        print("ChatModel — arnés de verificación (sin Xcode)")
        await autorSeCongelaPorMensaje()
        await elResultadoGanaALosDeltas()
        await cancelarNoDuplicaLaBurbuja()
        await elErrorNoInventaBurbuja()
        await elHistorialViajaSinElTurnoNuevo()
        print(failures == 0 ? "\nTODO VERDE" : "\n\(failures) FALLARON")
        exit(failures == 0 ? 0 : 1)
    }
}
