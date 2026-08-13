#if DEBUG
import Foundation

/// Dispara UN turno al arrancar, sólo cuando la app recibe `--sonda` por
/// launch argument. Existe porque el runner de XCUITest necesita un bundle id
/// propio y por tanto un perfil de aprovisionamiento que sólo una cuenta de
/// Apple en Xcode puede emitir — un atom de Bernard. La sonda prueba el turno
/// real sobre la app instalada sin bundle id nuevo, y su salida viaja por el
/// stdout que `devicectl --console` entrega a la Mac.
///
/// El flag NO se puede activar desde el teléfono: sólo lo pasa un lanzamiento
/// por cable. Si algún día el test de UI puede firmarse, esto se borra.
enum SondaDeTurno {
    static let bandera = "--sonda"
    /// Pide además una foto de la pantalla, que viaja en base64 por stdout.
    static let banderaFoto = "--foto"
    /// Mide cuánto tarda ABRIR una conversación, separando red de render.
    static let banderaAbrir = "--abrir"
    static let mensaje = "Responde únicamente con la palabra PONG"

    static func pedida(_ argumentos: [String] = CommandLine.arguments) -> Bool {
        argumentos.contains(bandera)
    }

    static func fotoPedida(_ argumentos: [String] = CommandLine.arguments) -> Bool {
        argumentos.contains(banderaFoto)
    }

    static func aperturaPedida(_ argumentos: [String] = CommandLine.arguments) -> Bool {
        argumentos.contains(banderaAbrir)
    }

    /// "Tarda mucho al abrir un chat" tiene dos causas opuestas —la red trayendo
    /// un JSON gordo, o la vista pintando cientos de mensajes— y el arreglo de
    /// una no sirve para la otra. Esto las separa midiendo TODAS: una sola
    /// conversación chica no dice nada del problema.
    @MainActor
    static func medirApertura(_ chat: ChatModel, _ conversations: ConversationsModel) async {
        await conversations.refresh()
        let candidatos = (conversations.pinned + conversations.active).prefix(10)
        print("[medir] midiendo \(candidatos.count) conversaciones")
        var peor = (titulo: "", segundos: 0.0, caracteres: 0)
        for resumen in candidatos where resumen.id != chat.conversationID {
            let t0 = Date()
            await chat.open(resumen.id)
            let segundos = Date().timeIntervalSince(t0)
            let caracteres = chat.messages.reduce(0) { $0 + $1.content.count }
            let queja = chat.errorMessage.map { " · ⚠️ \($0)" } ?? ""
            print("[medir] \(String(format: "%6.2f", segundos))s · \(chat.messages.count) msgs · \(caracteres) chars · \(resumen.title.prefix(34))\(queja)")
            if segundos > peor.segundos {
                peor = (String(resumen.title.prefix(38)), segundos, caracteres)
            }
        }
        print("[medir] LA PEOR: \(String(format: "%.2f", peor.segundos))s con \(peor.caracteres) caracteres · \(peor.titulo)")
    }

    @MainActor
    static func revisarLista(_ conversations: ConversationsModel) async {
        let t0 = Date()
        await conversations.refresh()
        print("[sonda] la lista tardó \(String(format: "%.1f", Date().timeIntervalSince(t0)))s")
        print("[sonda] lista: \(conversations.summaries.count) conversaciones · error: \(conversations.errorMessage ?? "ninguno")")
        print("[sonda] agrupadas → fijados \(conversations.pinned.count) · activos \(conversations.active.count) · archivados \(conversations.archived.count)")
        for resumen in conversations.summaries.prefix(5) {
            print("[sonda]   \(resumen.id) · \(resumen.title)")
        }
    }

    @MainActor
    static func correr(_ chat: ChatModel) async {
        print("[sonda] mandando: \(mensaje)")
        chat.send(mensaje)
        for _ in 0..<240 {
            if !chat.isStreaming { break }
            try? await Task.sleep(nanoseconds: 500_000_000)
        }
        if let ultimo = chat.messages.last, ultimo.role == .assistant {
            print("[sonda] respuesta en el hilo: \(ultimo.content)")
        } else {
            print("[sonda] SIN respuesta en el hilo · error: \(chat.errorMessage ?? "ninguno")")
        }
    }
}

#endif
