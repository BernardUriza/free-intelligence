import Foundation

// MARK: - contracts/agent-turn.vectors.json — la máquina del turno como contrato

func canonico(_ objeto: Any) -> String {
    guard let datos = try? JSONSerialization.data(withJSONObject: objeto, options: [.sortedKeys, .fragmentsAllowed]) else {
        return "<no-json>"
    }
    return String(decoding: datos, as: UTF8.self)
}

@MainActor
func proyeccionDelTurno(_ model: ChatModel) -> [String: Any] {
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
func losVectoresDelTurnoSeCumplen() async {
    print("agent-turn.vectors.json: la máquina del turno obedece el mismo contrato que core")
    let ruta = rutaDeContrato("agent-turn.vectors.json")
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

func contrato(_ nombre: String) -> [[String: Any]]? {
    let ruta = rutaDeContrato("\(nombre)")
    guard let datos = try? Data(contentsOf: ruta),
          let raiz = try? JSONSerialization.jsonObject(with: datos) as? [String: Any],
          let vectores = raiz["vectors"] as? [[String: Any]], !vectores.isEmpty else {
        expect(false, "el contrato existe y trae vectores: \(ruta.path)")
        return nil
    }
    return vectores
}

func mensajes(_ crudos: Any?) -> [ChatMessage] {
    (crudos as? [[String: Any]] ?? []).compactMap { m in
        guard let rol = ChatMessage.Role(rawValue: m["role"] as? String ?? "") else { return nil }
        return ChatMessage(role: rol, content: m["content"] as? String ?? "", timestamp: m["timestamp"] as? String)
    }
}

@MainActor
func losVectoresDeDerivacionesSeCumplen() async {
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
            expect(false, "\(nombre): kind desconocido «\(vector["kind"] as? String ?? "?")» — el arnés no lo implementa")
        }
        let esperado = canonico(vector["expect"] ?? NSNull())
        let visto = canonico(actual)
        expect(visto == esperado, "\(nombre)\n       esperado \(esperado)\n       actual   \(visto)")
    }
}

// MARK: - contracts/conversation-state.vectors.json

func eventosDeDesenlace(_ op: [String: Any]) -> [StreamEvent] {
    let texto = op["text"] as? String ?? ""
    let reacciones = op["reactions"] as? [String] ?? []
    var eventos: [StreamEvent] = [.open]
    if !texto.isEmpty { eventos.append(.text(texto)) }
    if !reacciones.isEmpty { eventos.append(.result(text: "", model: nil, reactions: reacciones)) }
    if op["deferred"] as? Bool == true { eventos.append(.deferred) }
    eventos.append(.done)
    return eventos
}

/// Cómo termina el stream de un vector: con frames, tronando el transporte,
/// colgado hasta que el usuario lo para (`stopped`), o retenido abierto hasta
/// que el arnés aplica lo que llega a mitad del turno (`merge_seed`).
indirect enum DesenlaceDelTurno {
    case eventos([StreamEvent])
    case falla
    case colgado
    case retenido(DesenlaceDelTurno)
}

func alimentar(_ c: AsyncThrowingStream<StreamEvent, Error>.Continuation, _ desenlace: DesenlaceDelTurno) {
    switch desenlace {
    case .falla:
        c.finish(throwing: Og118Error.unauthorized)
    case .colgado, .retenido:
        c.yield(.open)
    case .eventos(let eventos):
        for e in eventos { c.yield(e) }
        c.finish()
    }
}

/// Sin texto parcial la falla es un transporte que truena; con texto parcial es
/// un frame `error` a mitad del turno, que también revierte.
func desenlace(_ op: [String: Any], falla: Bool) -> DesenlaceDelTurno {
    if op["stopped"] as? Bool == true { return .colgado }
    guard falla else { return .eventos(eventosDeDesenlace(op)) }
    guard let parcial = op["partialText"] as? String, !parcial.isEmpty else { return .falla }
    return .eventos([.open, .text(parcial), .failure(op["message"] as? String ?? "error"), .done])
}

/// `saved` sólo se proyecta cuando el vector lo declara; entonces se mide, nunca se salta.
@MainActor
func proyeccionDelHilo(_ model: ChatModel, guardado: ConversationRecord?, esperado: Any?) -> [String: Any] {
    var proyeccion: [String: Any] = [
        "messages": model.messages.map { ["role": $0.role.rawValue, "content": $0.content] as [String: Any] },
        "failure": model.errorMessage == nil ? NSNull() : (model.tipoDeFalla == .vacio ? "empty" : "stream"),
        "unsentText": model.borradorNoEnviado?.texto ?? NSNull(),
        "lastSentText": model.ultimoEnvio?.texto ?? NSNull()
    ]
    if (esperado as? [String: Any])?["saved"] != nil {
        proyeccion["saved"] = guardado.map { r in
            r.messages.map { ["role": $0.role.rawValue, "content": $0.content] as [String: Any] }
        } ?? NSNull()
    }
    return proyeccion
}

@MainActor
func losVectoresDelHiloSeCumplen() async {
    print("conversation-state.vectors.json: envío, fold, falla, reintento e hidratación como en core")
    guard let vectores = contrato("conversation-state.vectors.json") else { return }
    for vector in vectores {
        let nombre = vector["name"] as? String ?? "?"
        let ops = vector["ops"] as? [[String: Any]] ?? []
        var cola: [DesenlaceDelTurno] = []
        var enVuelo: (AsyncThrowingStream<StreamEvent, Error>.Continuation, DesenlaceDelTurno)?
        let stream: ChatModel.Stream = { _, _, _, _, _, _ in
            let siguiente: DesenlaceDelTurno = cola.isEmpty ? .eventos([]) : cola.removeFirst()
            return AsyncThrowingStream { c in
                if case .retenido(let despues) = siguiente { enVuelo = (c, despues) }
                alimentar(c, siguiente)
            }
        }
        var semilla: ConversationRecord?
        if let primero = ops.first, primero["op"] as? String == "hydrate" {
            semilla = ConversationRecord.from(
                id: "v", messages: mensajes(primero["messages"]), createdAt: "2026-10-17T00:00:00Z", now: "2026-10-17T00:00:00Z"
            )
        }
        var registro = semilla
        var guardado: ConversationRecord?
        let model = ChatModel(
            conversationID: "v",
            stream: stream,
            persist: { guardado = $0 },
            restore: { _ in registro },
            pausa: {}
        )
        await model.restoreThread()
        func operar(_ op: [String: Any], en indice: Int) {
            switch op["op"] as? String ?? "" {
            case "hydrate":
                expect(indice == 0, "\(nombre): hydrate sólo abre el vector (el arnés lo restaura)")
            case "merge_seed":
                // La semilla ES la copia del servidor: el save la relee antes del PUT.
                registro = ConversationRecord.from(
                    id: "v", messages: mensajes(op["messages"]), createdAt: "2026-10-17T00:00:00Z", now: "2026-10-17T00:00:00Z"
                )
                model.unirHiloDelServidor(mensajes(op["messages"]))
            case "dismiss_failure":
                model.errorMessage = nil
            case "clear_unsent":
                model.borradorRestaurado()
            default:
                expect(false, "\(nombre): op desconocido «\(op["op"] as? String ?? "?")» — el arnés no lo implementa")
            }
        }
        var i = 0
        while i < ops.count {
            let op = ops[i]
            switch op["op"] as? String ?? "" {
            case "send", "retry":
                var parado = false
                var aMitad: [[String: Any]] = []
                var j = i + 1
                while j < ops.count, ops[j]["op"] as? String == "merge_seed" { j += 1 }
                if j < ops.count, let sig = ops[j]["op"] as? String, sig == "settled" || sig == "failed" {
                    parado = ops[j]["stopped"] as? Bool == true
                    aMitad = Array(ops[(i + 1)..<j])
                    let final = desenlace(ops[j], falla: sig == "failed")
                    cola.append(aMitad.isEmpty ? final : .retenido(final))
                    i = j
                } else {
                    cola.append(.eventos([]))
                }
                if op["op"] as? String == "send" {
                    model.send(op["text"] as? String ?? "")
                } else {
                    model.reintentar()
                }
                await settle()
                if !aMitad.isEmpty {
                    for (k, intermedia) in aMitad.enumerated() { operar(intermedia, en: i - aMitad.count + k) }
                    if let (c, despues) = enVuelo { alimentar(c, despues) }
                    enVuelo = nil
                    await settle()
                }
                if parado {
                    model.cancel()
                    await settle()
                }
            default:
                operar(op, en: i)
            }
            i += 1
        }
        await settle()
        let esperado = canonico(vector["expect"] ?? NSNull())
        let visto = canonico(proyeccionDelHilo(model, guardado: guardado, esperado: vector["expect"]))
        expect(visto == esperado, "\(nombre)\n       esperado \(esperado)\n       actual   \(visto)")
    }
}

@MainActor
func elAppendDelServidorNoSeDuplicaAlGuardar() async {
    print("el mensaje del worker que ya está en el servidor no se re-sube al guardar el turno")
    let ayer = [
        ChatMessage(role: .user, content: "ayer", timestamp: "2020-01-01T00:00:00Z"),
        ChatMessage(role: .assistant, content: "te contesté", timestamp: "2020-01-01T00:00:01Z")
    ]
    let worker = ChatMessage(role: .assistant, content: "listo el reporte", timestamp: "2999-01-01T00:00:00Z")
    let base = ConversationRecord.from(id: "w", messages: ayer, createdAt: "2020-01-01T00:00:00Z", now: "2020-01-01T00:00:01Z")
    let vivo = ConversationRecord.from(id: "w", messages: ayer + [worker], createdAt: "2020-01-01T00:00:00Z", now: "2999-01-01T00:00:00Z")
    var servidor = base
    var guardado: ConversationRecord?
    var turno: AsyncThrowingStream<StreamEvent, Error>.Continuation?
    let model = ChatModel(
        conversationID: "w",
        stream: { _, _, _, _, _, _ in AsyncThrowingStream { c in c.yield(.open); turno = c } },
        persist: { guardado = $0 },
        restore: { _ in servidor },
        now: { "2026-10-19T00:00:00Z" },
        pausa: {}
    )
    await model.restoreThread()
    model.send("hola")
    await settle()
    servidor = vivo
    model.unirHiloDelServidor(vivo.chatMessages)
    expect(model.isStreaming, "unir el hilo del servidor no toca el turno en vuelo")
    expect(model.messages.map(\.content) == ["ayer", "te contesté", "hola", "listo el reporte"],
           "el mensaje del worker se ordena por timestamp (\(model.messages.map(\.content)))")
    turno?.yield(.text("respuesta"))
    turno?.yield(.done)
    turno?.finish()
    await settle()
    let contenidos = guardado?.messages.map(\.content) ?? []
    expect(contenidos.filter { $0 == "listo el reporte" }.count == 1, "el worker queda UNA vez en lo guardado (\(contenidos))")
    expect(contenidos.contains("hola") && contenidos.last == "respuesta", "y el turno se guarda completo (\(contenidos))")
    expect(contenidos == ["ayer", "te contesté", "hola", "listo el reporte", "respuesta"],
           "y en el orden del hilo, como lo guarda la web (\(contenidos))")
}
