import Foundation
import Testing
@testable import og118

/// Micrófono y red falsos: el arranque se queda esperando hasta que el test
/// lo suelta, para observar el estado intermedio.
@MainActor
private final class DictadoFalso {
    var arranques = 0
    var detenciones = 0
    var despertares = 0
    var arranque: CheckedContinuation<Void, Error>?

    func dependencias(transcripcion: String = "  hola mundo  ") -> DictadoDependencias {
        DictadoDependencias(
            empezar: { [self] in
                arranques += 1
                try await withCheckedThrowingContinuation { arranque = $0 }
            },
            detener: { [self] in
                detenciones += 1
                return Data([1, 2, 3])
            },
            cancelar: {},
            transcribir: { _ in transcripcion },
            despertar: { [self] in despertares += 1 }
        )
    }
}

@MainActor
private func esperar(_ condicion: @MainActor () -> Bool) async {
    var vueltas = 0
    while !condicion() && vueltas < 10_000 {
        vueltas += 1
        await Task.yield()
    }
}

@MainActor
private func modelo(_ falso: DictadoFalso) -> VoiceModel {
    VoiceModel(servicio: VoiceService(accessToken: { "" }), dictado: falso.dependencias())
}

@MainActor
@Test func elMicPublicaQueGrabaYUnSegundoToqueNoArrancaOtraGrabadora() async {
    let falso = DictadoFalso()
    let voz = modelo(falso)
    var dictados: [String] = []

    voz.alternarDictado { dictados.append($0) }
    #expect(voz.preparando)
    #expect(!voz.grabando)
    await esperar { falso.arranque != nil }

    voz.alternarDictado { dictados.append($0) }
    #expect(falso.arranques == 1)

    falso.arranque?.resume()
    await esperar { voz.grabando }
    #expect(voz.grabando)
    #expect(!voz.preparando)
    await esperar { falso.despertares == 1 }
    #expect(falso.despertares == 1)

    voz.alternarDictado { dictados.append($0) }
    #expect(!voz.grabando)
    #expect(voz.transcribiendo)
    #expect(falso.detenciones == 1)
    await esperar { !voz.transcribiendo }
    #expect(dictados == ["hola mundo"])
}

@MainActor
@Test func unMicrofonoQueFallaDejaElBotonLibreYAvisa() async {
    let falso = DictadoFalso()
    let voz = modelo(falso)

    voz.alternarDictado { _ in }
    await esperar { falso.arranque != nil }
    falso.arranque?.resume(throwing: VoiceError.audioSinRespuesta)
    await esperar { !voz.preparando }

    #expect(!voz.grabando)
    #expect(voz.errorMessage == VoiceError.audioSinRespuesta.localizedDescription)
}

@MainActor
@Test func despertarSeDisparaAlTocar() async {
    let falso = DictadoFalso()
    let voz = modelo(falso)
    voz.alternarDictado { _ in }
    await esperar { falso.despertares == 1 }
    #expect(falso.despertares == 1)
    #expect(voz.preparando)
}
