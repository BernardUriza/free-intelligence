import Foundation
#if os(iOS)
import AVFoundation
#endif

/// Voz contra el servidor de og118: `POST /tts/synthesize` devuelve el audio
/// crudo con su Content-Type, y `POST /stt/transcribe` recibe un multipart y
/// devuelve `{text}`. Los límites son los del servidor, no inventados:
/// 4096 caracteres de texto y 25 MB de audio.
enum VoiceLimits {
    static let maxTextChars = 4096
    static let maxAudioBytes = 25 * 1024 * 1024
    /// iOS graba AAC en contenedor MPEG-4 y el servidor acepta `audio/m4a`,
    /// así que no hay que transcodificar nada.
    static let recordingMime = "audio/m4a"
}

enum VoiceError: LocalizedError {
    case notConfigured
    case tooLong(Int)
    case tooLarge(Int)
    case upstream(Int)
    case sinPermiso
    case sinGrabacion

    var errorDescription: String? {
        switch self {
        case .notConfigured:
            return "La voz no está configurada en el servidor."
        case .tooLong(let n):
            return "El texto es muy largo para leerlo (\(n) caracteres; máximo \(VoiceLimits.maxTextChars))."
        case .tooLarge(let n):
            return "La grabación pesa demasiado (\(n / 1_048_576) MB; máximo 25 MB)."
        case .upstream(let code):
            return "El servicio de voz respondió \(code)."
        case .sinPermiso:
            return "Falta permiso de micrófono. Actívalo en Ajustes."
        case .sinGrabacion:
            return "No se grabó nada."
        }
    }
}

private struct TTSRequest: Encodable {
    let text: String
    let responseFormat: String
    let speed: Double

    enum CodingKeys: String, CodingKey {
        case text
        case speed
        case responseFormat = "response_format"
    }
}

private struct TranscriptResponse: Decodable {
    let text: String
}

struct VoiceService {
    var accessToken: () async throws -> String

    /// Devuelve el audio y su Content-Type, que el reproductor necesita para
    /// elegir decodificador.
    func synthesize(text: String, speed: Double = 1.0) async throws -> (Data, String) {
        let recortado = String(text.prefix(VoiceLimits.maxTextChars))
        var request = URLRequest(url: Config.apiBase.appendingPathComponent("tts/synthesize"))
        request.httpMethod = "POST"
        request.timeoutInterval = 120
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        try await authorize(&request)
        request.httpBody = try JSONEncoder().encode(
            TTSRequest(text: recortado, responseFormat: "mp3", speed: speed)
        )

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw Og118Error.notHTTP }
        if http.statusCode == 503 { throw VoiceError.notConfigured }
        guard (200..<300).contains(http.statusCode) else {
            throw VoiceError.upstream(http.statusCode)
        }
        let tipo = http.value(forHTTPHeaderField: "Content-Type") ?? "audio/mpeg"
        return (data, tipo)
    }

    func transcribe(audio: Data, mime: String = VoiceLimits.recordingMime) async throws -> String {
        guard !audio.isEmpty else { throw VoiceError.sinGrabacion }
        guard audio.count <= VoiceLimits.maxAudioBytes else {
            throw VoiceError.tooLarge(audio.count)
        }

        let frontera = "og118-\(UUID().uuidString)"
        var request = URLRequest(url: Config.apiBase.appendingPathComponent("stt/transcribe"))
        request.httpMethod = "POST"
        request.timeoutInterval = 120
        request.setValue(
            "multipart/form-data; boundary=\(frontera)",
            forHTTPHeaderField: "Content-Type"
        )
        try await authorize(&request)
        request.httpBody = cuerpoMultipart(audio: audio, mime: mime, frontera: frontera)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw Og118Error.notHTTP }
        if http.statusCode == 503 { throw VoiceError.notConfigured }
        guard (200..<300).contains(http.statusCode) else {
            throw VoiceError.upstream(http.statusCode)
        }
        return try JSONDecoder().decode(TranscriptResponse.self, from: data).text
    }

    private func cuerpoMultipart(audio: Data, mime: String, frontera: String) -> Data {
        var cuerpo = Data()
        func agregar(_ texto: String) { cuerpo.append(Data(texto.utf8)) }
        agregar("--\(frontera)\r\n")
        agregar("Content-Disposition: form-data; name=\"audio\"; filename=\"chunk.m4a\"\r\n")
        agregar("Content-Type: \(mime)\r\n\r\n")
        cuerpo.append(audio)
        agregar("\r\n--\(frontera)--\r\n")
        return cuerpo
    }

    private func authorize(_ request: inout URLRequest) async throws {
        let token = try await accessToken()
        if !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
    }
}

#if os(iOS)
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

@MainActor
final class SpeechPlayer: NSObject, ObservableObject {
    @Published private(set) var hablando: String?

    private var player: AVAudioPlayer?

    func reproducir(_ audio: Data, id: String) throws {
        detener()
        try AVAudioSession.sharedInstance().setCategory(.playback, mode: .spokenAudio)
        try AVAudioSession.sharedInstance().setActive(true)
        let reproductor = try AVAudioPlayer(data: audio)
        reproductor.delegate = self
        reproductor.play()
        player = reproductor
        hablando = id
    }

    func detener() {
        player?.stop()
        player = nil
        hablando = nil
    }
}

extension SpeechPlayer: AVAudioPlayerDelegate {
    nonisolated func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        Task { @MainActor in
            self.player = nil
            self.hablando = nil
        }
    }
}
#endif
