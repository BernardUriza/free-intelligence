import Foundation

/// El único camino por el que una petición sale hacia el servidor de og118.
/// Un 401 con el token cacheado no es el fin de la sesión: se refresca una vez
/// y se repite; sólo si el servidor rechaza también el token nuevo se cierra.
struct Transporte {
    var token: (_ rechazado: String?) async throws -> String
    var sesionRechazada: () async -> Void
    var datos: (URLRequest) async throws -> (Data, URLResponse) = {
        try await URLSession.shared.data(for: $0)
    }

    func autorizada(_ request: URLRequest, rechazado: String? = nil) async throws -> (URLRequest, String) {
        let token = try await token(rechazado)
        guard !token.isEmpty else { throw Og118Error.unauthorized }
        var firmada = request
        firmada.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        firmada.setValue(Config.clienteID, forHTTPHeaderField: "X-OG118-Client")
        return (firmada, token)
    }

    func enviar(_ request: URLRequest, despertador: Bool = false) async throws -> (Data, HTTPURLResponse) {
        var rechazado: String?
        for _ in 0..<2 {
            let (firmada, token) = try await autorizada(request, rechazado: rechazado)
            let (data, response) = try await conDespertador(firmada, despertador)
            guard let http = response as? HTTPURLResponse else { throw Og118Error.notHTTP }
            guard http.statusCode == 401 else { return (data, http) }
            rechazado = token
        }
        await sesionRechazada()
        throw Og118Error.unauthorized
    }

    private func conDespertador(_ request: URLRequest, _ despertador: Bool) async throws -> (Data, URLResponse) {
        guard despertador else { return try await datos(request) }
        return try await ArranqueEnFrio.conReintento { esReintento in
            var conPlazo = request
            conPlazo.timeoutInterval = esReintento ? 60 : ArranqueEnFrio.plazoDespertador
            return try await datos(conPlazo)
        }
    }
}
