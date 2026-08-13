import Foundation
#if os(iOS)
import AVFoundation

/// Graba con AVAudioRecorder en AAC/m4a — el formato nativo de iOS y uno de los
/// que el servidor acepta, así que el audio viaja sin transcodificar.
@MainActor
final class AudioRecorder: ObservableObject {
    @Published private(set) var grabando = false

    private var recorder: AVAudioRecorder?
    private var destino: URL?

    func pedirPermiso() async -> Bool {
        await withCheckedContinuation { continuation in
            AVAudioApplication.requestRecordPermission { concedido in
                continuation.resume(returning: concedido)
            }
        }
    }

    func empezar() async throws {
        guard await pedirPermiso() else { throw VoiceError.sinPermiso }

        let sesion = AVAudioSession.sharedInstance()
        try sesion.setCategory(.playAndRecord, mode: .spokenAudio, options: [.defaultToSpeaker])
        try sesion.setActive(true)

        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("og118-\(UUID().uuidString).m4a")
        let ajustes: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 16_000,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.medium.rawValue
        ]
        let grabadora = try AVAudioRecorder(url: url, settings: ajustes)
        grabadora.record()
        recorder = grabadora
        destino = url
        grabando = true
    }

    /// Detiene y devuelve el audio. Borra el temporal: la grabación ya viajó en
    /// memoria y dejarla en disco es residuo con voz del usuario dentro.
    func detener() -> Data? {
        recorder?.stop()
        recorder = nil
        grabando = false
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        guard let url = destino else { return nil }
        destino = nil
        defer { try? FileManager.default.removeItem(at: url) }
        return try? Data(contentsOf: url)
    }

    func cancelar() {
        recorder?.stop()
        recorder = nil
        grabando = false
        if let url = destino { try? FileManager.default.removeItem(at: url) }
        destino = nil
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }
}
#endif
