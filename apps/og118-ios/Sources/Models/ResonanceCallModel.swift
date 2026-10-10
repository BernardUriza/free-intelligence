import Foundation
#if os(iOS)
import AVFoundation

/// El `useOg118ResonanceCall` del iPhone: une micrófono, VAD, STT, el turno
/// del chat y el TTS al `ResonanceController`, que es el único que decide.
@MainActor
final class ResonanceCallModel: NSObject, ObservableObject {
    @Published private(set) var estado: ResonanceState = .idle
    @Published private(set) var bandas: [Double] = []
    @Published private(set) var oyendo = false

    var activa: Bool { estado != .idle && estado != .ended }
    var etiqueta: String? { ResonancePolicy.etiqueta(estado, oyendo: oyendo) }

    private let chat: ChatModel
    private let servicio: VoiceService
    private let alFallar: (String) -> Void
    private let controlador = ResonanceController()
    private let microfono = ResonanceMicrophone()
    private let cues = ResonanceCuePlayer()
    private var compuerta = ResonanceVadGate()
    private var reloj: Timer?
    private var autoResume: Task<Void, Never>?
    private var dormir: Task<Void, Never>?
    private var limite: Task<Void, Never>?
    private var tts: AVAudioPlayer?
    private var finDeTts: CheckedContinuation<Void, Never>?

    /// `alFallar` es el banner de voz: la web enruta `onError` a `setVoiceError`.
    init(chat: ChatModel, servicio: VoiceService, alFallar: @escaping (String) -> Void) {
        self.chat = chat
        self.servicio = servicio
        self.alFallar = alFallar
        super.init()
        controlador.alEfecto = { [weak self] efecto in self?.ejecutar(efecto) }
        controlador.alEvento = { [weak self] evento, previo, siguiente in
            self?.cues.aplicar(ResonanceCuePolicy.acciones(previo: previo, siguiente: siguiente, evento: evento))
            self?.alCambiar(siguiente)
        }
    }

    convenience init(chat: ChatModel, client: Og118Client, alFallar: @escaping (String) -> Void) {
        self.init(chat: chat, servicio: VoiceService(accessToken: client.accessToken), alFallar: alFallar)
    }

    func alternar() {
        activa ? colgar() : llamar()
    }

    func llamar() {
        compuerta.reset()
        cues.detenerTodo()
        limite?.cancel()
        limite = Task { [weak self] in
            try? await Task.sleep(nanoseconds: ResonancePolicy.maxCallMs * 1_000_000)
            guard !Task.isCancelled, let self else { return }
            self.alFallar(ResonancePolicy.mensajeDeFallo(fase: .duration, error: nil, fatal: true))
            self.colgar()
        }
        arrancarReloj()
        controlador.empezarLlamada()
    }

    func colgar() {
        limite?.cancel()
        controlador.colgar()
    }

    private func alCambiar(_ siguiente: ResonanceState) {
        estado = siguiente
        if siguiente == .silenceHold {
            if autoResume == nil {
                autoResume = Task { [weak self] in
                    try? await Task.sleep(nanoseconds: ResonancePolicy.autoResumeMs * 1_000_000)
                    guard !Task.isCancelled else { return }
                    self?.autoResume = nil
                    self?.controlador.enviar(.silenceResume)
                }
            }
            if dormir == nil {
                dormir = Task { [weak self] in
                    try? await Task.sleep(nanoseconds: ResonancePolicy.idleHangupMs * 1_000_000)
                    guard !Task.isCancelled else { return }
                    self?.dormir = nil
                    self?.controlador.enviar(.sleepDecayStarted)
                    self?.controlador.colgar()
                }
            }
        } else {
            autoResume?.cancel()
            autoResume = nil
            dormir?.cancel()
            dormir = nil
        }
    }

    private func arrancarReloj() {
        reloj?.invalidate()
        let intervalo = Double(ResonancePolicy.tickMs) / 1000
        reloj = Timer.scheduledTimer(withTimeInterval: intervalo, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.tick() }
        }
    }

    private func tick() {
        let modo = ResonancePolicy.modoVad(controlador.estado)
        let nivel = microfono.nivel
        bandas = microfono.bandas
        oyendo = controlador.estado == .listening && nivel >= ResonancePolicy.silenceThreshold
        let ahora = ProcessInfo.processInfo.systemUptime * 1000
        switch compuerta.tick(nivel: nivel, ahoraMs: ahora, modo: modo) {
        case .speechStart: controlador.enviar(.userSpeechStarted)
        case .speechEnd: controlador.enviar(.userSpeechEnded)
        case .bargeIn: controlador.interrumpir()
        case nil: break
        }
    }

    private func ejecutar(_ efecto: ResonanceEffect) {
        switch efecto {
        case .openMic:
            Task {
                do {
                    try await microfono.abrir()
                    try microfono.empezarSegmento()
                } catch {
                    alFallar(ResonancePolicy.mensajeDeFallo(fase: .mic, error: error, fatal: true))
                    controlador.fallaFatal()
                }
            }
        case .beginTranscribe:
            Task {
                do {
                    guard let audio = microfono.terminarSegmento() else { return controlador.fallaRecuperable() }
                    let texto = try await servicio.transcribe(audio: audio, mime: "audio/wav")
                        .trimmingCharacters(in: .whitespacesAndNewlines)
                    guard !texto.isEmpty else { return controlador.fallaRecuperable() }
                    controlador.sttCompleto(texto)
                } catch {
                    recuperar(.stt, error)
                }
            }
        case .invokeAgent:
            Task {
                do {
                    let respuesta = try await turnoDelAgente(controlador.transcripcion ?? "")
                    guard !respuesta.isEmpty else { return controlador.fallaRecuperable() }
                    controlador.respuestaLista(respuesta)
                } catch {
                    recuperar(.agent, error)
                }
            }
        case .speak:
            Task {
                do {
                    try await hablar(controlador.textoAsistente ?? "")
                    if controlador.estado == .speaking { controlador.enviar(.assistantSpeechCompleted) }
                } catch {
                    recuperar(.tts, error)
                }
            }
        case .stopSpeaking:
            callarTts()
        case .holdSilence:
            break
        case .fadeAndHangup, .endCall:
            cerrarTodo()
        }
    }

    private func recuperar(_ fase: ResonancePolicy.Fase, _ error: Error) {
        alFallar(ResonancePolicy.mensajeDeFallo(fase: fase, error: error, fatal: false))
        controlador.fallaRecuperable()
    }

    /// El MISMO turno que el hilo persiste (el `sendAndAwait` de la web): la
    /// llamada nunca habla una respuesta que no quedó escrita.
    private func turnoDelAgente(_ texto: String) async throws -> String {
        let antes = chat.messages.count
        chat.send(texto)
        guard chat.isStreaming else { throw ResonanceError.turnoRechazado }
        while chat.isStreaming {
            try await Task.sleep(nanoseconds: 100_000_000)
        }
        if let error = chat.errorMessage { throw ResonanceError.agente(error) }
        guard chat.messages.count > antes, let ultimo = chat.messages.last, ultimo.role == .assistant else {
            throw ResonanceError.turnoRechazado
        }
        return ultimo.content
    }

    /// Se resuelve cuando el audio TERMINA; la falla de reproducción resuelve
    /// (cortar es semántica de barge-in), la de síntesis se propaga.
    private func hablar(_ texto: String) async throws {
        guard !texto.isEmpty else { return }
        let (audio, _) = try await servicio.synthesize(text: texto)
        guard controlador.estado == .speaking else { return }
        await withCheckedContinuation { (continuation: CheckedContinuation<Void, Never>) in
            guard let reproductor = try? AVAudioPlayer(data: audio) else { return continuation.resume() }
            reproductor.delegate = self
            tts = reproductor
            finDeTts = continuation
            if !reproductor.play() { terminarTts() }
        }
    }

    private func callarTts() {
        tts?.stop()
        terminarTts()
    }

    fileprivate func terminarTts() {
        tts = nil
        let pendiente = finDeTts
        finDeTts = nil
        pendiente?.resume()
    }

    private func cerrarTodo() {
        reloj?.invalidate()
        reloj = nil
        callarTts()
        cues.detenerTodo()
        microfono.cerrar()
        compuerta.reset()
        bandas = []
        oyendo = false
        autoResume?.cancel()
        dormir?.cancel()
        limite?.cancel()
        autoResume = nil
        dormir = nil
    }
}

extension ResonanceCallModel: AVAudioPlayerDelegate {
    nonisolated func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        Task { @MainActor in self.terminarTts() }
    }

    nonisolated func audioPlayerDecodeErrorDidOccur(_ player: AVAudioPlayer, error: Error?) {
        Task { @MainActor in self.terminarTts() }
    }
}

enum ResonanceError: LocalizedError {
    case turnoRechazado
    case agente(String)

    var errorDescription: String? {
        switch self {
        case .turnoRechazado: return "El agente no pudo responder este turno."
        case .agente(let mensaje): return mensaje
        }
    }
}
#endif
