import Foundation

// MARK: - Plan glass-box: los frames que antes caían en `break`

@MainActor
func elPlanYLosPasosSePintan() async {
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
func nadaDesaparecEnSilencio() async {
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
func elPlanNoSeArrastraEntreTurnos() async {
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

func laSondaNoSeDisparaSola() {
    print("la sonda de turno NO existe sin su bandera")
    expect(SondaDeTurno.pedida([]) == false, "sin argumentos no hay sonda")
    expect(SondaDeTurno.pedida(["/App", "-NSTreatUnknownArgumentsAsOpen", "YES"]) == false,
           "los argumentos normales de un lanzamiento no la disparan")
    expect(SondaDeTurno.pedida(["/App", "--sonda"]), "con la bandera sí")
}

// MARK: - El ciclo de vida del plan (los 5 frames que llegaban como "sin mapear")

@MainActor
func elGuardBloqueaYSeVE() async {
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
func cancelarElPlanNoEsCompletarlo() async {
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
func elDesenlaceDelPlanLlega() async {
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
func laEnmiendaViveEntreElAnuncioYElPlanNuevo() async {
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

func losFramesDelPlanYaNoSonBasura() {
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
