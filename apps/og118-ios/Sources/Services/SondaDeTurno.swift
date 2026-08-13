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
    static let mensaje = "Responde únicamente con la palabra PONG"

    static func pedida(_ argumentos: [String] = CommandLine.arguments) -> Bool {
        argumentos.contains(bandera)
    }

    /// Manda el turno y reporta lo que quedó EN EL HILO, no lo que llegó por la
    /// red: que los frames lleguen no prueba que la burbuja exista. Si el
    /// doblado se rompiera, la consola diría "sin respuesta" con los frames en
    /// verde, que es exactamente la falla que hay que poder ver.
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
