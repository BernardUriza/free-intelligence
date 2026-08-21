import Foundation
#if os(iOS)
import AVFoundation

/// Reproduce el audio que devuelve `/tts/synthesize`. Hermano de AudioRecorder:
/// misma frontera —hardware de audio, sólo iOS— y misma forma observable.
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
