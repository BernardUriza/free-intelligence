import Foundation
#if os(iOS)
import AVFoundation

/// `setActive`, `setCategory` y `engine.start` bloquean hasta que el servidor de
/// audio contesta: en el hilo principal congelaban la app (medido con `sample`).
enum ColaDeAudio {
    private static let cola = DispatchQueue(label: "og118.audio-session", qos: .userInitiated)
    static let limiteDeActivacion: TimeInterval = 8

    /// Con `limite`, un servidor de audio que no contesta se vuelve un error con
    /// nombre en vez de una llamada que dice «Escuchando…» para siempre.
    static func ejecutar<T>(limite: TimeInterval? = nil, _ trabajo: @escaping () throws -> T) async throws -> T {
        try await withCheckedThrowingContinuation { continuation in
            let respuesta = UnaSolaVez(continuation)
            cola.async { respuesta.entregar(Result { try trabajo() }) }
            if let limite {
                DispatchQueue.global().asyncAfter(deadline: .now() + limite) {
                    respuesta.entregar(.failure(VoiceError.audioSinRespuesta))
                }
            }
        }
    }

    static func activar(_ categoria: AVAudioSession.Category, modo: AVAudioSession.Mode, opciones: AVAudioSession.CategoryOptions = []) async throws {
        try await ejecutar(limite: limiteDeActivacion) {
            let sesion = AVAudioSession.sharedInstance()
            try sesion.setCategory(categoria, mode: modo, options: opciones)
            try sesion.setActive(true)
        }
    }

    /// Soltar la sesión no tiene a quién avisarle si falla: se encola y ya.
    static func desactivar() {
        cola.async {
            try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        }
    }
}

/// La continuación se resuelve con lo que llegue primero: el trabajo o el límite.
private final class UnaSolaVez<T>: @unchecked Sendable {
    private var continuation: CheckedContinuation<T, Error>?
    private let candado = NSLock()

    init(_ continuation: CheckedContinuation<T, Error>) { self.continuation = continuation }

    func entregar(_ resultado: Result<T, Error>) {
        candado.lock()
        let pendiente = continuation
        continuation = nil
        candado.unlock()
        pendiente?.resume(with: resultado)
    }
}
#endif
