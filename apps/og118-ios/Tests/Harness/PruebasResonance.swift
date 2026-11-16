import Foundation

// MARK: - Resonance: el núcleo de la llamada, mismo contrato que fi-glass

func resonanceElNucleoDeLaLlamada() {
    print("resonance: máquina, efectos, cues, VAD y escala del analizador")
    let r = ResonanceMachine.reducir
    expect(r(.idle, .callStarted) == .listening, "llamar abre a escuchar")
    expect(r(.listening, .userSpeechEnded) == .transcribing, "fin de habla transcribe")
    expect(r(.transcribing, .sttCompleted) == .thinking, "la transcripción pasa a pensar")
    expect(r(.thinking, .assistantSpeechStarted) == .speaking, "la respuesta se habla")
    expect(r(.speaking, .assistantSpeechCompleted) == .silenceHold, "al terminar de hablar, silencio")
    expect(r(.silenceHold, .silenceResume) == .listening, "el auto-resume vuelve a escuchar")
    expect(r(.speaking, .userSpeechStarted) == .interrupted, "hablar encima interrumpe")
    expect(r(.thinking, .errorRecoverable) == .listening, "un fallo recuperable vuelve a escuchar")
    expect(r(.idle, .errorRecoverable) == .idle, "en reposo un fallo no arranca nada")
    expect(r(.transcribing, .errorFatal) == .ended, "un fallo fatal cuelga")
    expect(r(.ended, .callStarted) == .ended, "colgada es terminal")
    expect(r(.silenceHold, .userSpeechStarted) == .silenceHold, "en silencio la voz no cambia de estado, como la web")

    var efectos: [ResonanceEffect] = []
    let c = ResonanceController()
    c.alEfecto = { efectos.append($0) }
    c.empezarLlamada()
    c.enviar(.userSpeechEnded)
    c.sttCompleto("hola")
    c.respuestaLista("qué tal")
    c.interrumpir()
    expect(efectos == [.openMic, .beginTranscribe, .invokeAgent, .speak, .stopSpeaking, .openMic],
           "el turno completo despacha los efectos de la web en orden, con barge-in")
    expect(c.transcripcion == "hola" && c.textoAsistente == "qué tal", "guarda transcripción y respuesta")
    c.colgar()
    expect(c.estado == .ended && efectos.last == .endCall, "colgar despacha end_call")
    c.empezarLlamada()
    expect(c.estado == .listening, "una llamada nueva reinicia un controlador ya colgado")

    let p = ResonanceCuePolicy.acciones
    expect(p(.listening, .transcribing, .userSpeechEnded) == [.playLoop(.thinking), .playOnce(.crystalline)],
           "fin de habla: arranca el loop y suena el cristal")
    expect(p(.transcribing, .thinking, .sttCompleted) == [], "transcribir→pensar no reinicia el loop")
    expect(p(.thinking, .speaking, .assistantSpeechStarted) == [.stopLoop(.thinking)], "salir de pensar lo detiene")
    expect(p(.thinking, .listening, .errorRecoverable) == [.stopLoop(.thinking)], "un error tampoco lo deja colgado")
    expect(p(.speaking, .silenceHold, .assistantSpeechCompleted) == [.playOnce(.ready)], "al terminar suena «ready»")
    expect(p(.thinking, .ended, .callEnded) == [.stopAll], "colgar silencia todo")

    var g = ResonanceVadGate()
    expect(g.tick(nivel: 30, ahoraMs: 0, modo: .detect) == nil, "la voz no se declara antes de 180 ms")
    expect(g.tick(nivel: 30, ahoraMs: 180, modo: .detect) == .speechStart, "a los 180 ms sostenidos sí")
    expect(g.tick(nivel: 18, ahoraMs: 600, modo: .detect) == nil, "entre umbrales sigue siendo voz (histéresis)")
    expect(g.tick(nivel: 5, ahoraMs: 1000, modo: .detect) == nil, "silencio corto no cierra el turno")
    expect(g.tick(nivel: 5, ahoraMs: 1450, modo: .detect) == .speechEnd, "850 ms de silencio lo cierran")
    var largo = ResonanceVadGate()
    _ = largo.tick(nivel: 40, ahoraMs: 0, modo: .detect)
    _ = largo.tick(nivel: 40, ahoraMs: 200, modo: .detect)
    expect(largo.tick(nivel: 40, ahoraMs: 20_200, modo: .detect) == .speechEnd, "un turno se corta a los 20 s")
    var barge = ResonanceVadGate()
    _ = barge.tick(nivel: 30, ahoraMs: 0, modo: .barge)
    expect(barge.tick(nivel: 30, ahoraMs: 200, modo: .barge) == .bargeIn, "hablar encima del TTS dispara barge-in")
    expect(barge.tick(nivel: 30, ahoraMs: 400, modo: .barge) == nil, "una sola vez por interrupción")
    expect(ResonancePolicy.modoVad(.thinking) == .idle && ResonancePolicy.modoVad(.silenceHold) == .detect,
           "el modo del VAD sale del estado como en la web")

    var s = ResonanceSpectrum()
    let silencio = ResonanceSpectrum.nivel(s.bytes(Array(repeating: 0, count: 256)))
    expect(silencio == 0, "silencio digital = nivel 0, como getByteFrequencyData")
    // Fixture: AnalyserNode de Chrome (OfflineAudioContext 48 kHz, seno 1 kHz ×0.3, ganancia 2.5,
    // smoothing 0) leído en el frame 2560. El puerto debe dar los mismos bytes.
    let chrome: [UInt8] = [90, 93, 88, 195, 255, 255, 255, 255, 139, 90, 81, 67, 53, 40, 29, 19, 10, 1]
        + [UInt8](repeating: 0, count: 110)
    var exacto = ResonanceSpectrum(smoothing: 0)
    let tono = (2304..<2560).map { Float(0.3 * sin(2 * Double.pi * 1000 * Double($0) / 48_000)) * ResonancePolicy.gain }
    let propios = exacto.bytes(tono)
    let peor = zip(propios, chrome).map { abs(Int($0) - Int($1)) }.max() ?? 255
    expect(peor <= 1, "los 128 bins coinciden con el AnalyserNode de Chrome (peor diferencia \(peor))")
    var semilla: UInt64 = 7
    let vozAncha = (0..<256).map { _ -> Float in
        semilla = semilla &* 6364136223846793005 &+ 1442695040888963407
        return (Float(semilla >> 40) / Float(1 << 24) * 2 - 1) * 0.05 * ResonancePolicy.gain
    }
    var ancha = ResonanceSpectrum()
    var nivelVoz = 0.0
    for _ in 0..<20 { nivelVoz = ResonanceSpectrum.nivel(ancha.bytes(vozAncha)) }
    expect(nivelVoz > 24, "una señal de banda ancha a 0.05 cruza el umbral de 24 (midió \(Int(nivelVoz)); Chrome mide 166)")
    var debil = ResonanceSpectrum()
    let ruido = (0..<256).map { Float(0.0002 * sin(2 * Double.pi * 300 * Double($0) / 48_000)) * ResonancePolicy.gain }
    var nivelRuido = 0.0
    for _ in 0..<20 { nivelRuido = ResonanceSpectrum.nivel(debil.bytes(ruido)) }
    expect(nivelRuido < 13, "un murmullo de fondo queda bajo el piso de 13 (midió \(Int(nivelRuido)))")
    expect(ResonanceSpectrum.bandas([UInt8](repeating: 255, count: 128), cuantas: 24, ganancia: 2.5).allSatisfy { $0 == 1 },
           "las bandas se recortan a 1")
    expect(ResonancePolicy.etiqueta(.speaking, oyendo: false) == "Hablando — puedes interrumpir"
           && ResonancePolicy.etiqueta(.listening, oyendo: true) == "Te oigo", "las etiquetas son las de la web")
}
