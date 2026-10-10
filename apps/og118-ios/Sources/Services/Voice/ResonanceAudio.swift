import Foundation
#if os(iOS)
import AVFoundation

/// El micrófono de la llamada: UN motor que alimenta a la vez el analizador
/// (VAD + ecualizador) y el segmento WAV que viaja a `/stt/transcribe`.
@MainActor
final class ResonanceMicrophone {
    private(set) var nivel: Double = 0
    private(set) var bandas: [Double] = []

    private let motor = AVAudioEngine()
    private var analizador = ResonanceSpectrum()
    private var ventana: [Float] = []
    private var segmento: AVAudioFile?
    private var segmentoURL: URL?
    private var abierto = false

    func pedirPermiso() async -> Bool {
        await withCheckedContinuation { continuation in
            AVAudioApplication.requestRecordPermission { continuation.resume(returning: $0) }
        }
    }

    /// `voiceChat` activa la cancelación de eco, igual que `getUserMedia` en el
    /// navegador: sin ella el TTS del altavoz dispararía el barge-in.
    func abrir() async throws {
        if abierto { return }
        guard await pedirPermiso() else { throw VoiceError.sinPermiso }
        let sesion = AVAudioSession.sharedInstance()
        try sesion.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker, .allowBluetoothHFP])
        try sesion.setActive(true)
        let entrada = motor.inputNode
        try entrada.setVoiceProcessingEnabled(true)
        let formato = entrada.outputFormat(forBus: 0)
        entrada.installTap(onBus: 0, bufferSize: 1024, format: formato) { [weak self] buffer, _ in
            guard let canal = buffer.floatChannelData?[0] else { return }
            let muestras = Array(UnsafeBufferPointer(start: canal, count: Int(buffer.frameLength)))
            let copia = Self.mono(buffer)
            Task { @MainActor in self?.recibir(muestras, copia: copia) }
        }
        motor.prepare()
        try motor.start()
        abierto = true
    }

    func cerrar() {
        guard abierto else { return }
        motor.inputNode.removeTap(onBus: 0)
        motor.stop()
        abierto = false
        descartarSegmento()
        nivel = 0
        bandas = []
        analizador.reset()
        ventana = []
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    func empezarSegmento() throws {
        guard segmento == nil else { return }
        let formato = motor.inputNode.outputFormat(forBus: 0)
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("resonance-\(UUID().uuidString).wav")
        let ajustes: [String: Any] = [
            AVFormatIDKey: kAudioFormatLinearPCM,
            AVSampleRateKey: formato.sampleRate,
            AVNumberOfChannelsKey: 1,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: false
        ]
        segmento = try AVAudioFile(forWriting: url, settings: ajustes, commonFormat: .pcmFormatFloat32, interleaved: false)
        segmentoURL = url
    }

    /// Cierra el segmento y devuelve sus bytes; el temporal se borra porque
    /// lleva la voz del usuario dentro.
    func terminarSegmento() -> Data? {
        guard let url = segmentoURL else { return nil }
        segmento = nil
        segmentoURL = nil
        defer { try? FileManager.default.removeItem(at: url) }
        return try? Data(contentsOf: url)
    }

    private func descartarSegmento() {
        if let url = segmentoURL { try? FileManager.default.removeItem(at: url) }
        segmento = nil
        segmentoURL = nil
    }

    private func recibir(_ muestras: [Float], copia: AVAudioPCMBuffer?) {
        if let segmento, let copia { try? segmento.write(from: copia) }
        ventana.append(contentsOf: muestras.map { $0 * ResonancePolicy.gain })
        if ventana.count > analizador.fftSize { ventana.removeFirst(ventana.count - analizador.fftSize) }
        let bytes = analizador.bytes(ventana)
        nivel = ResonanceSpectrum.nivel(bytes)
        bandas = ResonanceSpectrum.bandas(bytes, cuantas: ResonancePolicy.bandCount, ganancia: Double(ResonancePolicy.gain))
    }

    private nonisolated static func mono(_ buffer: AVAudioPCMBuffer) -> AVAudioPCMBuffer? {
        guard let origen = buffer.floatChannelData?[0],
              let formato = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: buffer.format.sampleRate, channels: 1, interleaved: false),
              let copia = AVAudioPCMBuffer(pcmFormat: formato, frameCapacity: buffer.frameLength),
              let destino = copia.floatChannelData?[0]
        else { return nil }
        copia.frameLength = buffer.frameLength
        destino.update(from: origen, count: Int(buffer.frameLength))
        return copia
    }
}

/// Los tres cues de la web (`/sounds/*.mp3`), con el mismo volumen 0.6 de
/// `createAudioCuePlayer`; el loop es idempotente como en el controlador web.
@MainActor
final class ResonanceCuePlayer {
    private var reproductores: [ResonanceCue: AVAudioPlayer] = [:]
    private var loops: Set<ResonanceCue> = []
    static let volumen: Float = 0.6

    init() {
        for cue in ResonanceCue.allCases {
            guard let url = Bundle.main.url(forResource: cue.rawValue, withExtension: "mp3"),
                  let reproductor = try? AVAudioPlayer(contentsOf: url) else { continue }
            reproductor.volume = Self.volumen
            reproductor.prepareToPlay()
            reproductores[cue] = reproductor
        }
    }

    func aplicar(_ acciones: [ResonanceCueAction]) {
        for accion in acciones {
            switch accion {
            case .playLoop(let cue):
                guard !loops.contains(cue), let r = reproductores[cue] else { continue }
                loops.insert(cue)
                r.numberOfLoops = -1
                r.currentTime = 0
                r.play()
            case .stopLoop(let cue):
                guard loops.contains(cue) else { continue }
                loops.remove(cue)
                reproductores[cue]?.stop()
            case .playOnce(let cue):
                guard let r = reproductores[cue] else { continue }
                r.numberOfLoops = 0
                r.currentTime = 0
                r.play()
            case .stopAll:
                detenerTodo()
            }
        }
    }

    func detenerTodo() {
        reproductores.values.forEach { $0.stop() }
        loops.removeAll()
    }
}
#endif
