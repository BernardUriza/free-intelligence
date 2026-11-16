import Foundation

// MARK: - El parser contra BYTES REALES del servidor

func elParserLeeUnTurnoDeVerdad() {
    print("SSEParser contra la captura real de /chat/stream")
    // Capturado con curl contra el server og118 corriendo local, mismo código
    // que el de Azure. Si el contrato del servidor cambia, esto se pone rojo
    // aquí y no en el teléfono de Bernard.
    let ruta = rutaDeContrato("fixtures/turno-real.sse")
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

func elParserAguantaLoQueElServidorPuedeMandar() {
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

// MARK: - normalizeStreamedMarkdown portado de fi-glass

func elMarkdownPegadoSeRepara() {
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
