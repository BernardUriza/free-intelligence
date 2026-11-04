import Foundation
import Testing
@testable import og118

@MainActor
private final class EmisorFalso {
    var intercambios = 0
    var pendientes: [CheckedContinuation<TokenResponse, Error>] = []
    var pendiente: CheckedContinuation<TokenResponse, Error>? { pendientes.last }

    func resolver(_ resultado: Result<TokenResponse, Error>) {
        let colas = pendientes
        pendientes = []
        colas.forEach { $0.resume(with: resultado) }
    }

    func dependencias() -> AuthDependencies {
        AuthDependencies(
            exchange: { [self] _ in
                await MainActor.run { intercambios += 1 }
                return try await withCheckedThrowingContinuation { c in
                    Task { @MainActor in pendientes.append(c) }
                }
            },
            keychainRead: { "refresh-guardado" },
            keychainSave: { _ in true },
            keychainDelete: {}
        )
    }
}

@MainActor
private func esperar(_ condicion: @MainActor () -> Bool) async {
    var vueltas = 0
    while !condicion() && vueltas < 20_000 {
        vueltas += 1
        await Task.yield()
    }
}

@MainActor
@Test func tresCallersConcurrentesCompartenUnSoloRefresh() async throws {
    let emisor = EmisorFalso()
    let auth = Auth(deps: emisor.dependencias())
    #expect(auth.isSignedIn)

    async let a = auth.token()
    async let b = auth.token()
    async let c = auth.token()
    await esperar { emisor.pendiente != nil }
    await esperar { false }
    #expect(emisor.intercambios == 1)

    emisor.resolver(.success(TokenResponse(accessToken: "acceso-1", refreshToken: "refresh-2", expiresIn: 3600)))
    let tokens = try await [a, b, c]
    #expect(tokens == ["acceso-1", "acceso-1", "acceso-1"])

    let cuarto = try await auth.token()
    #expect(cuarto == "acceso-1")
    #expect(emisor.intercambios == 1)
}

@MainActor
@Test func unRefreshRechazadoDeslogueaYElSiguienteCallerNoRepite() async {
    let emisor = EmisorFalso()
    let auth = Auth(deps: emisor.dependencias())
    async let a = auth.token()
    await esperar { emisor.pendiente != nil }
    emisor.resolver(.failure(AuthError.rejected(403)))
    let resultado = try? await a
    #expect(resultado == nil)
    #expect(!auth.isSignedIn)
}
