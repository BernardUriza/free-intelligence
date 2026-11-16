import Foundation
import ImageIO
import UniformTypeIdentifiers

// MARK: - Adjuntar imágenes (paridad con useComposerImages de fi-glass)

func imagenDePrueba(ancho: Int, alto: Int, ruido: Bool, tipo: UTType) -> Data {
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

func dimensiones(_ base64: String) -> (Int, Int)? {
    guard let datos = Data(base64Encoded: base64),
          let fuente = CGImageSourceCreateWithData(datos as CFData, nil),
          let props = CGImageSourceCopyPropertiesAtIndex(fuente, 0, nil) as? [CFString: Any],
          let w = props[kCGImagePropertyPixelWidth] as? Int,
          let h = props[kCGImagePropertyPixelHeight] as? Int else { return nil }
    return (w, h)
}

func imagenAdjuntaComoLaWeb() {
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
func adjuntosTopanEnCuatro() async {
    print("adjuntos: el quinto se rechaza con el mensaje de la web")
    let modelo = AdjuntosModel()
    let chica = imagenDePrueba(ancho: 40, alto: 40, ruido: false, tipo: .png)
    await modelo.agregar((1...5).map { AdjuntosModel.Archivo(datos: chica, nombre: "f\($0).png") })
    expect(modelo.borradores.count == 4, "se quedan 4 (hay \(modelo.borradores.count))")
    expect(modelo.error == "Máximo 4 imágenes por mensaje.", "y el quinto avisa, no desaparece en silencio")
    expect(modelo.lugaresLibres == 0, "sin lugares libres el + se deshabilita")
}

@MainActor
func laImagenViajaYSePersiste() async {
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
func reintentarConservaLaImagen() async {
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
