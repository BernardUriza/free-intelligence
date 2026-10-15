import Foundation

/// Dictado y lectura en voz alta. Vive aparte del turno porque son capacidades
/// que fallan por su cuenta: que el TTS no esté configurado no debe impedir
/// escribir, ni un error de dictado tumbar la conversación.
#if os(iOS)
/// Micrófono y red entran inyectados: los tests recorren los estados del
/// dictado sin permiso de micrófono ni servidor.
struct DictadoDependencias {
    var empezar: @MainActor () async throws -> Void
    var detener: @MainActor () -> Data?
    var cancelar: @MainActor () -> Void
    var transcribir: @MainActor (Data) async throws -> String
    var despertar: @MainActor () async -> Void
}

@MainActor
final class VoiceModel: ObservableObject {
    @Published private(set) var preparando = false
    @Published private(set) var grabando = false
    @Published private(set) var transcribiendo = false
    @Published private(set) var sintetizando: String?
    @Published var errorMessage: String?

    let reproductor = SpeechPlayer()

    private let servicio: VoiceService
    private let dictado: DictadoDependencias

    init(servicio: VoiceService, dictado: DictadoDependencias) {
        self.servicio = servicio
        self.dictado = dictado
    }

    convenience init(client: Og118Client) {
        let servicio = VoiceService(accessToken: client.accessToken)
        let grabadora = AudioRecorder()
        self.init(
            servicio: servicio,
            dictado: DictadoDependencias(
                empezar: { try await grabadora.empezar() },
                detener: { grabadora.detener() },
                cancelar: { grabadora.cancelar() },
                transcribir: { try await servicio.transcribe(audio: $0) },
                despertar: { await servicio.despertar() }
            )
        )
    }

    /// Un toque graba, el siguiente transcribe. Mientras el micrófono se
    /// prepara o el audio viaja, los toques se ignoran: nunca dos grabadoras.
    func alternarDictado(alTranscribir: @escaping (String) -> Void) {
        if grabando {
            grabando = false
            guard let audio = dictado.detener() else {
                errorMessage = VoiceError.sinGrabacion.localizedDescription
                return
            }
            transcribiendo = true
            Task {
                defer { transcribiendo = false }
                do {
                    let texto = try await dictado.transcribir(audio)
                    let limpio = texto.trimmingCharacters(in: .whitespacesAndNewlines)
                    if !limpio.isEmpty { alTranscribir(limpio) }
                } catch {
                    errorMessage = error.localizedDescription
                }
            }
            return
        }
        guard !preparando, !transcribiendo else { return }
        errorMessage = nil
        preparando = true
        Task { await dictado.despertar() }
        Task {
            defer { preparando = false }
            do {
                try await dictado.empezar()
                grabando = true
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }

    func cancelarDictado() {
        dictado.cancelar()
        grabando = false
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
                try await reproductor.reproducir(audio, id: id)
            } catch {
                errorMessage = error.localizedDescription
            }
        }
    }
}
#endif
