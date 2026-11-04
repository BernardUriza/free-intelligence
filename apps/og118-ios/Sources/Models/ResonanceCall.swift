import Foundation

/// RESONANCE, el modo llamada: puerto 1:1 del núcleo de fi-glass
/// (`resonanceCallMachine`, `resonanceEffects`, `resonanceCuePolicy`, `resonanceVadGate`).
enum ResonanceState: String, CaseIterable {
    case idle, listening, transcribing, thinking, speaking, interrupted
    case silenceHold = "silence_hold"
    case sleepDecay = "sleep_decay"
    case ended
}

enum ResonanceEvent: String {
    case callStarted = "call.started"
    case micOpened = "mic.opened"
    case userSpeechStarted = "user.speech.started"
    case userSpeechEnded = "user.speech.ended"
    case sttCompleted = "stt.completed"
    case assistantSpeechStarted = "assistant.speech.started"
    case assistantSpeechInterrupted = "assistant.speech.interrupted"
    case assistantSpeechCompleted = "assistant.speech.completed"
    case silenceDetected = "silence.detected"
    case silenceResume = "silence.resume"
    case sleepDecayStarted = "sleep.decay.started"
    case errorRecoverable = "error.recoverable"
    case errorFatal = "error.fatal"
    case callEnded = "call.ended"
}

enum ResonanceMachine {
    private static let transiciones: [ResonanceState: [ResonanceEvent: ResonanceState]] = [
        .idle: [.callStarted: .listening],
        .listening: [
            .micOpened: .listening,
            .userSpeechStarted: .listening,
            .userSpeechEnded: .transcribing,
            .silenceDetected: .silenceHold
        ],
        .transcribing: [.sttCompleted: .thinking],
        .thinking: [.assistantSpeechStarted: .speaking],
        .speaking: [.userSpeechStarted: .interrupted, .assistantSpeechCompleted: .silenceHold],
        .interrupted: [.assistantSpeechInterrupted: .listening],
        .silenceHold: [.silenceResume: .listening, .sleepDecayStarted: .sleepDecay],
        .sleepDecay: [.silenceResume: .listening],
        .ended: [:]
    ]

    /// La recuperación es global, como en la web: un fallo recuperable vuelve a
    /// escuchar desde cualquier fase activa; uno fatal (micrófono) cuelga.
    static func reducir(_ estado: ResonanceState, _ evento: ResonanceEvent) -> ResonanceState {
        if estado == .ended { return estado }
        if evento == .callEnded || evento == .errorFatal { return .ended }
        if evento == .errorRecoverable { return estado == .idle ? .idle : .listening }
        return transiciones[estado]?[evento] ?? estado
    }
}

enum ResonanceEffect: Equatable {
    case openMic, beginTranscribe, invokeAgent, speak, stopSpeaking, holdSilence, fadeAndHangup, endCall

    static func alEntrar(_ estado: ResonanceState) -> ResonanceEffect? {
        switch estado {
        case .idle: return nil
        case .listening: return .openMic
        case .transcribing: return .beginTranscribe
        case .thinking: return .invokeAgent
        case .speaking: return .speak
        case .interrupted: return .stopSpeaking
        case .silenceHold: return .holdSilence
        case .sleepDecay: return .fadeAndHangup
        case .ended: return .endCall
        }
    }
}

enum ResonanceCue: String, CaseIterable {
    case thinking, crystalline, ready
}

enum ResonanceCueAction: Equatable {
    case playLoop(ResonanceCue)
    case stopLoop(ResonanceCue)
    case playOnce(ResonanceCue)
    case stopAll
}

enum ResonanceCuePolicy {
    /// El loop de "pensando" cubre transcribir + pensar y se detiene al SALIR de
    /// esa fase, no por un evento: así ninguna transición lo deja colgado.
    static func acciones(previo: ResonanceState, siguiente: ResonanceState, evento: ResonanceEvent) -> [ResonanceCueAction] {
        if evento == .callEnded || evento == .errorFatal || siguiente == .ended { return [.stopAll] }
        var acciones: [ResonanceCueAction] = []
        let procesaba = previo == .transcribing || previo == .thinking
        let procesa = siguiente == .transcribing || siguiente == .thinking
        if !procesaba && procesa { acciones.append(.playLoop(.thinking)) }
        if procesaba && !procesa { acciones.append(.stopLoop(.thinking)) }
        if evento == .userSpeechEnded { acciones.append(.playOnce(.crystalline)) }
        if evento == .assistantSpeechCompleted { acciones.append(.playOnce(.ready)) }
        return acciones
    }
}

/// Los umbrales son los de `DEFAULT_VAD_CONFIG` de fi-glass, en la MISMA escala
/// (0-255, promedio de `getByteFrequencyData`) gracias a `ResonanceSpectrum`.
struct ResonanceVadConfig: Equatable {
    var speechOnThreshold: Double = 24
    var speechOffThreshold: Double = 13
    var minSpeechMs: Double = 180
    var endSilenceMs: Double = 850
    var maxTurnMs: Double = 20_000
}

enum ResonanceVadMode { case detect, barge, idle }

enum ResonanceVadEvent: Equatable { case speechStart, speechEnd, bargeIn }

struct ResonanceVadGate {
    let config: ResonanceVadConfig
    private var enHabla = false
    private var candidatoDesde: Double?
    private var hablaDesde: Double = 0
    private var ultimaVoz: Double = 0
    private var bargeEnganchado = false

    init(config: ResonanceVadConfig = ResonanceVadConfig()) {
        self.config = config
    }

    mutating func reset() {
        enHabla = false
        candidatoDesde = nil
        hablaDesde = 0
        ultimaVoz = 0
        bargeEnganchado = false
    }

    mutating func tick(nivel: Double, ahoraMs: Double, modo: ResonanceVadMode) -> ResonanceVadEvent? {
        if modo == .idle {
            reset()
            return nil
        }
        let sobreOn = nivel >= config.speechOnThreshold
        if modo == .barge {
            if nivel <= config.speechOffThreshold {
                bargeEnganchado = false
                candidatoDesde = nil
                return nil
            }
            if bargeEnganchado { return nil }
            if sobreOn {
                let desde = candidatoDesde ?? ahoraMs
                candidatoDesde = desde
                if ahoraMs - desde >= config.minSpeechMs {
                    candidatoDesde = nil
                    bargeEnganchado = true
                    return .bargeIn
                }
            }
            return nil
        }
        let bajoOff = nivel <= config.speechOffThreshold
        if !enHabla {
            if sobreOn {
                let desde = candidatoDesde ?? ahoraMs
                candidatoDesde = desde
                if ahoraMs - desde >= config.minSpeechMs {
                    enHabla = true
                    hablaDesde = ahoraMs
                    ultimaVoz = ahoraMs
                    candidatoDesde = nil
                    return .speechStart
                }
            } else {
                candidatoDesde = nil
            }
            return nil
        }
        if nivel > config.speechOffThreshold { ultimaVoz = ahoraMs }
        if ahoraMs - hablaDesde >= config.maxTurnMs || (bajoOff && ahoraMs - ultimaVoz >= config.endSilenceMs) {
            enHabla = false
            candidatoDesde = nil
            return .speechEnd
        }
        return nil
    }
}

/// Políticas de tiempo de `useResonanceCallLoop` (DEFAULT_SILENCE, DEFAULT_SLEEP).
enum ResonancePolicy {
    static let autoResumeMs: UInt64 = 1_200
    static let idleHangupMs: UInt64 = 300_000
    static let maxCallMs: UInt64 = 600_000
    static let tickMs: UInt64 = 50
    /// `useAudioAnalysis`: SILENCE_THRESHOLD 2 decide el «Te oigo»; GAIN 2.5 es la ganancia previa al analizador.
    static let silenceThreshold: Double = 2
    static let gain: Float = 2.5
    static let bandCount = 24

    static func modoVad(_ estado: ResonanceState, bargeIn: Bool = true) -> ResonanceVadMode {
        switch estado {
        case .listening, .silenceHold: return .detect
        case .speaking where bargeIn: return .barge
        default: return .idle
        }
    }

    /// Las etiquetas de `RESONANCE_LABEL` en Og118AgentChat.tsx.
    static func etiqueta(_ estado: ResonanceState, oyendo: Bool) -> String? {
        if oyendo { return "Te oigo" }
        switch estado {
        case .idle: return nil
        case .listening: return "Escuchando…"
        case .transcribing: return "Transcribiendo…"
        case .thinking: return "Pensando…"
        case .speaking: return "Hablando — puedes interrumpir"
        case .interrupted: return "Te oigo — interrumpiendo"
        case .silenceHold: return "Sigo aquí"
        case .sleepDecay: return "Bajando volumen…"
        case .ended: return "Llamada finalizada"
        }
    }

    static func visualizadorActivo(_ estado: ResonanceState) -> Bool {
        estado == .listening || estado == .speaking || estado == .silenceHold
    }

    /// `mensajeDeFalloDeVoz` de useOg118ResonanceCall: el mensaje conocido gana;
    /// si no hay, cae a la fase, y un fallo recuperable avisa que se reintenta.
    static func mensajeDeFallo(fase: Fase, error: Error?, fatal: Bool) -> String {
        if let error, !error.localizedDescription.trimmingCharacters(in: .whitespaces).isEmpty,
           !(error is CancellationError) {
            return error.localizedDescription
        }
        return fatal ? fase.fallo : "\(fase.fallo) Reintentando."
    }

    enum Fase {
        case mic, duration, stt, agent, tts

        var fallo: String {
            switch self {
            case .mic: return "No se pudo abrir el micrófono — la llamada se colgó."
            case .duration: return "La llamada alcanzó su límite de duración."
            case .stt: return "No se pudo transcribir tu voz."
            case .agent: return "El agente no pudo responder este turno."
            case .tts: return "No se pudo sintetizar la respuesta en voz."
            }
        }
    }
}

/// `AnalyserNode.getByteFrequencyData` de Web Audio, según la spec: ventana
/// Blackman, FFT normalizada, suavizado temporal y mapeo dB→byte.
struct ResonanceSpectrum {
    let fftSize: Int
    let smoothing: Double
    let minDecibels: Double
    let maxDecibels: Double
    private var suavizado: [Double]
    private let ventana: [Double]
    private let cosenos: [[Double]]
    private let senos: [[Double]]

    init(fftSize: Int = 256, smoothing: Double = 0.8, minDecibels: Double = -100, maxDecibels: Double = -30) {
        self.fftSize = fftSize
        self.smoothing = smoothing
        self.minDecibels = minDecibels
        self.maxDecibels = maxDecibels
        let n = Double(fftSize)
        ventana = (0..<fftSize).map { i in
            let x = Double(i) / n
            return 0.42 - 0.5 * cos(2 * .pi * x) + 0.08 * cos(4 * .pi * x)
        }
        let bins = fftSize / 2
        cosenos = (0..<bins).map { k in (0..<fftSize).map { i in cos(2 * .pi * Double(k * i) / n) } }
        senos = (0..<bins).map { k in (0..<fftSize).map { i in sin(2 * .pi * Double(k * i) / n) } }
        suavizado = Array(repeating: 0, count: bins)
    }

    /// Toma las últimas `fftSize` muestras (ya con ganancia) y devuelve los bytes por bin.
    mutating func bytes(_ muestras: [Float]) -> [UInt8] {
        let bins = fftSize / 2
        var entrada = Array(repeating: 0.0, count: fftSize)
        let inicio = max(0, muestras.count - fftSize)
        let tomadas = muestras.count - inicio
        for i in 0..<tomadas {
            entrada[fftSize - tomadas + i] = Double(muestras[inicio + i]) * ventana[fftSize - tomadas + i]
        }
        var salida = [UInt8](repeating: 0, count: bins)
        let escala = 255 / (maxDecibels - minDecibels)
        for k in 0..<bins {
            var re = 0.0, im = 0.0
            let c = cosenos[k], s = senos[k]
            for i in 0..<fftSize {
                re += entrada[i] * c[i]
                im -= entrada[i] * s[i]
            }
            let magnitud = (re * re + im * im).squareRoot() / Double(fftSize)
            suavizado[k] = smoothing * suavizado[k] + (1 - smoothing) * magnitud
            let db = suavizado[k] > 0 ? 20 * log10(suavizado[k]) : -Double.infinity
            let byte = (escala * (db - minDecibels)).rounded(.down)
            salida[k] = UInt8(max(0, min(255, byte.isFinite ? byte : 0)))
        }
        return salida
    }

    mutating func reset() {
        suavizado = Array(repeating: 0, count: fftSize / 2)
    }

    static func nivel(_ bytes: [UInt8]) -> Double {
        bytes.isEmpty ? 0 : Double(bytes.reduce(0) { $0 + Int($1) }) / Double(bytes.count)
    }

    /// `frequencyDataToBands` de useAudioAnalysis: descarta el 25% alto y promedia.
    static func bandas(_ datos: [UInt8], cuantas: Int, ganancia: Double) -> [Double] {
        guard cuantas > 0, !datos.isEmpty else { return Array(repeating: 0, count: max(0, cuantas)) }
        let utiles = Int(Double(datos.count) * 0.75) > 0 ? Int(Double(datos.count) * 0.75) : datos.count
        let rebanada = max(1, utiles / cuantas)
        return (0..<cuantas).map { b in
            let inicio = b * rebanada
            var suma = 0.0, n = 0.0
            var i = inicio
            while i < inicio + rebanada && i < utiles {
                suma += Double(datos[i])
                n += 1
                i += 1
            }
            let escalado = (n > 0 ? suma / n : 0) / 255 * ganancia
            return min(1, max(0, escalado))
        }
    }
}

/// `resonanceCallController`: guarda el estado y, en cada CAMBIO, despacha el
/// efecto de entrada. Sin audio ni UI, para que el arnés pruebe el contrato.
final class ResonanceController {
    private(set) var estado: ResonanceState = .idle
    private(set) var transcripcion: String?
    private(set) var textoAsistente: String?
    private(set) var eventos: [ResonanceEvent] = []

    var alEfecto: (ResonanceEffect) -> Void = { _ in }
    var alEvento: (_ evento: ResonanceEvent, _ previo: ResonanceState, _ siguiente: ResonanceState) -> Void = { _, _, _ in }

    @discardableResult
    func enviar(_ evento: ResonanceEvent) -> ResonanceState {
        let previo = estado
        let siguiente = ResonanceMachine.reducir(estado, evento)
        eventos.append(evento)
        alEvento(evento, previo, siguiente)
        if siguiente != estado {
            estado = siguiente
            if let efecto = ResonanceEffect.alEntrar(estado) { alEfecto(efecto) }
        }
        return estado
    }

    func empezarLlamada() {
        estado = .idle
        transcripcion = nil
        textoAsistente = nil
        eventos = []
        enviar(.callStarted)
    }

    func sttCompleto(_ texto: String) {
        transcripcion = texto
        enviar(.sttCompleted)
    }

    func respuestaLista(_ texto: String) {
        textoAsistente = texto
        enviar(.assistantSpeechStarted)
    }

    /// Barge-in: corta el TTS y reabre el micrófono para el turno nuevo.
    func interrumpir() {
        guard estado == .speaking else { return }
        enviar(.userSpeechStarted)
        enviar(.assistantSpeechInterrupted)
    }

    func fallaRecuperable() {
        if estado != .ended && estado != .idle { enviar(.errorRecoverable) }
    }

    func fallaFatal() {
        if estado != .ended { enviar(.errorFatal) }
    }

    func colgar() {
        if estado != .ended { enviar(.callEnded) }
    }

    var activa: Bool { estado != .idle && estado != .ended }
}
