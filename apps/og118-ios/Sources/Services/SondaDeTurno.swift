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
    static let mensaje = "Responde únicamente con la palabra PONG"

    static func pedida(_ argumentos: [String] = CommandLine.arguments) -> Bool {
        argumentos.contains(bandera)
    }

    static func fotoPedida(_ argumentos: [String] = CommandLine.arguments) -> Bool {
        argumentos.contains(banderaFoto)
    }

    /// Manda el turno y reporta lo que quedó EN EL HILO, no lo que llegó por la
    /// red: que los frames lleguen no prueba que la burbuja exista. Si el
    /// doblado se rompiera, la consola diría "sin respuesta" con los frames en
    /// verde, que es exactamente la falla que hay que poder ver.
    /// La lista de chats vacía tiene dos causas opuestas y la misma pinta: que
    /// el servidor no devuelva nada para esta identidad, o que devuelva algo
    /// que el cliente no supo decodificar. El error las separa.
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
