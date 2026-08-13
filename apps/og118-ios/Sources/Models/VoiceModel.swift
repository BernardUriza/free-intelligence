import Foundation

/// Dictado y lectura en voz alta. Vive aparte del turno porque son capacidades
/// que fallan por su cuenta: que el TTS no esté configurado no debe impedir
/// escribir, ni un error de dictado tumbar la conversación.
#if os(iOS)
@MainActor
final class VoiceModel: ObservableObject {
    @Published private(set) var transcribiendo = false
    @Published private(set) var sintetizando: String?
    @Published var errorMessage: String?

    let grabadora = AudioRecorder()
    let reproductor = SpeechPlayer()

    private let servicio: VoiceService

    init(servicio: VoiceService) {
        self.servicio = servicio
    }

    convenience init(client: Og118Client) {
        self.init(servicio: VoiceService(accessToken: client.accessToken))
    }

    var grabando: Bool { grabadora.grabando }

    func alternarDictado(alTranscribir: @escaping (String) -> Void) {
        if grabadora.grabando {
            guard let audio = grabadora.detener() else {
                errorMessage = VoiceError.sinGrabacion.localizedDescription
                return
            }
            transcribiendo = true
            Task {
                defer { transcribiendo = false }
                do {
                    let texto = try await servicio.transcribe(audio: audio)
                    let limpio = texto.trimmingCharacters(in: .whitespacesAndNewlines)
                    if !limpio.isEmpty { alTranscribir(limpio) }
                } catch {
                    errorMessage = error.localizedDescription
                }
            }
        } else {
            errorMessage = nil
            Task {
                do { try await grabadora.empezar() } catch {
                    errorMessage = error.localizedDescription
                }
            }
        }
    }

    func cancelarDictado() {
        grabadora.cancelar()
    }

    /// Segundo toque en el mismo mensaje = detener. Sin eso, la única salida de
    /// una lectura larga es cerrar la app.
    func alternarLectura(de texto: String, id: String) {
        if reproductor.hablando == id {
            reproductor.detener()
            return
        }
        reproductor.detener()
        sintetizando = id
        Task {
            defer { sintetizando = nil }
            do {
                let (audio, _) = try await servicio.synthesize(text: texto)
                try reproductor.reproducir(audio, id: id)
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }
}
#endif
