import Foundation

// MARK: - El autor: objeto canónico, no string

func elAutorSeLeeEnLasDosFormas() {
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

func elAutorSeEscribeCanonico() {
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

func guardarNoAmputaElRecordDeLaWeb() {
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
func cambiarDeChatNoArrastraElReintento() async {
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
