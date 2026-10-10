import AuthenticationServices
import CryptoKit
import Foundation

private extension Data {
    var base64URLEncoded: String {
        base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}

enum Keychain {
    private static var service: String { "\(Config.bundleIdentifier).auth" }
    private static let account = "auth0-refresh-token"

    private static var base: [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
    }

    @discardableResult
    static func save(_ value: String) -> Bool {
        SecItemDelete(base as CFDictionary)
        var query = base
        query[kSecValueData as String] = Data(value.utf8)
        query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        return SecItemAdd(query as CFDictionary, nil) == errSecSuccess
    }

    static func read() -> String? {
        var query = base
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func delete() {
        SecItemDelete(base as CFDictionary)
    }
}

struct TokenResponse: Decodable {
    let accessToken: String
    let refreshToken: String?
    let expiresIn: Int?
    var idToken: String? = nil

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case expiresIn = "expires_in"
        case idToken = "id_token"
    }
}

enum AuthError: LocalizedError {
    case missingClientID
    case noCode
    case rejected(Int)
    case transport(String)
    case notSignedIn

    /// Solo un rechazo explícito del emisor invalida la sesión guardada. Un fallo
    /// de transporte (sin red, timeout, DNS) NO puede borrar credenciales: en un
    /// teléfono eso significaría deslogueo cada vez que se cae la señal.
    var revokesSession: Bool {
        if case .rejected(let code) = self { return (400...403).contains(code) }
        return false
    }

    var errorDescription: String? {
        switch self {
        case .missingClientID:
            return "Falta el client ID de Auth0 para la app nativa."
        case .noCode:
            return "Auth0 no devolvió un código de autorización."
        case .rejected(let code):
            return "Auth0 rechazó la petición (\(code))."
        case .transport(let detail):
            return "No se pudo contactar a Auth0: \(detail)"
        case .notSignedIn:
            return "No hay sesión activa."
        }
    }
}

struct AuthDependencies {
    var exchange: ([String: String]) async throws -> TokenResponse
    var keychainRead: () -> String?
    var keychainSave: (String) -> Bool
    var keychainDelete: () -> Void

    static let live = AuthDependencies(
        exchange: { body in
            var request = URLRequest(url: URL(string: "https://\(Config.auth0Domain)/oauth/token")!)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: body)

            let data: Data
            let response: URLResponse
            do {
                (data, response) = try await URLSession.shared.data(for: request)
            } catch {
                throw AuthError.transport(error.localizedDescription)
            }

            guard let http = response as? HTTPURLResponse else {
                throw AuthError.transport("respuesta no HTTP")
            }
            guard (200..<300).contains(http.statusCode) else {
                throw AuthError.rejected(http.statusCode)
            }
            do {
                return try JSONDecoder().decode(TokenResponse.self, from: data)
            } catch {
                throw AuthError.transport("respuesta ilegible")
            }
        },
        keychainRead: Keychain.read,
        keychainSave: Keychain.save,
        keychainDelete: Keychain.delete
    )
}

@MainActor
final class Auth: NSObject, ObservableObject {
    @Published private(set) var isSignedIn = false
    @Published private(set) var storageWarning: String?
    /// El correo del id_token, para el «Salir · correo» del drawer. Se recuerda
    /// entre lanzamientos para no pintar el pie vacío mientras viaja el refresh.
    @Published private(set) var email: String? = UserDefaults.standard.string(forKey: Auth.emailKey)
    private static let emailKey = "og118.email"

    private let deps: AuthDependencies
    private var accessToken: String?
    private var refreshToken: String?
    private var expiresAt: Date?

    init(deps: AuthDependencies = .live) {
        self.deps = deps
        super.init()
        refreshToken = deps.keychainRead()
        isSignedIn = refreshToken != nil
    }

    func signIn() async throws {
        let clientID = Config.auth0ClientID
        guard !clientID.isEmpty else { throw AuthError.missingClientID }

        let verifier = Self.randomVerifier()
        let callbackURL = try await authorize(clientID: clientID, verifier: verifier)

        guard
            let items = URLComponents(url: callbackURL, resolvingAgainstBaseURL: false)?.queryItems,
            let code = items.first(where: { $0.name == "code" })?.value
        else { throw AuthError.noCode }

        try await requestToken(body: [
            "grant_type": "authorization_code",
            "client_id": clientID,
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": Config.redirectURI
        ])
    }

    func token() async throws -> String {
        if let accessToken, let expiresAt, expiresAt > Date().addingTimeInterval(60) {
            return accessToken
        }
        guard let refreshToken else {
            signOut()
            throw AuthError.notSignedIn
        }
        do {
            try await requestToken(body: [
                "grant_type": "refresh_token",
                "client_id": Config.auth0ClientID,
                "refresh_token": refreshToken
            ])
        } catch {
            if (error as? AuthError)?.revokesSession == true { signOut() }
            throw error
        }
        guard let accessToken else { throw AuthError.notSignedIn }
        return accessToken
    }

    func signOut() {
        accessToken = nil
        refreshToken = nil
        expiresAt = nil
        deps.keychainDelete()
        email = nil
        UserDefaults.standard.removeObject(forKey: Self.emailKey)
        isSignedIn = false
    }

    private func requestToken(body: [String: String]) async throws {
        let decoded = try await deps.exchange(body)
        accessToken = decoded.accessToken
        if let newRefresh = decoded.refreshToken {
            refreshToken = newRefresh
            storageWarning = deps.keychainSave(newRefresh)
                ? nil
                : "No se pudo guardar la sesión en el Keychain: al reabrir la app habrá que iniciar sesión otra vez."
        }
        expiresAt = Date().addingTimeInterval(TimeInterval(decoded.expiresIn ?? 3600))
        if let correo = decoded.idToken.flatMap(Self.correo(deIdToken:)) {
            email = correo
            UserDefaults.standard.set(correo, forKey: Self.emailKey)
        }
        isSignedIn = true
    }

    /// Sin validar firma a propósito: el token llegó por TLS directo de Auth0 y
    /// el correo sólo se pinta, no autoriza nada.
    static func correo(deIdToken token: String) -> String? {
        let partes = token.split(separator: ".")
        guard partes.count >= 2 else { return nil }
        var base64 = String(partes[1])
            .replacingOccurrences(of: "-", with: "+")
            .replacingOccurrences(of: "_", with: "/")
        base64 += String(repeating: "=", count: (4 - base64.count % 4) % 4)
        guard let datos = Data(base64Encoded: base64),
              let claims = try? JSONSerialization.jsonObject(with: datos) as? [String: Any]
        else { return nil }
        return claims["email"] as? String
    }

    private func authorize(clientID: String, verifier: String) async throws -> URL {
        var components = URLComponents()
        components.scheme = "https"
        components.host = Config.auth0Domain
        components.path = "/authorize"
        components.queryItems = [
            URLQueryItem(name: "client_id", value: clientID),
            URLQueryItem(name: "response_type", value: "code"),
            URLQueryItem(name: "redirect_uri", value: Config.redirectURI),
            URLQueryItem(name: "scope", value: Config.auth0Scope),
            URLQueryItem(name: "audience", value: Config.auth0Audience),
            URLQueryItem(name: "code_challenge", value: Self.challenge(for: verifier)),
            URLQueryItem(name: "code_challenge_method", value: "S256")
        ]

        let url = components.url!
        return try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(
                url: url,
                callbackURLScheme: Config.callbackScheme
            ) { callback, error in
                if let error {
                    continuation.resume(throwing: error)
                } else if let callback {
                    continuation.resume(returning: callback)
                } else {
                    continuation.resume(throwing: AuthError.noCode)
                }
            }
            session.presentationContextProvider = self
            session.prefersEphemeralWebBrowserSession = false
            session.start()
        }
    }

    private static func randomVerifier() -> String {
        var bytes = [UInt8](repeating: 0, count: 32)
        _ = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        return Data(bytes).base64URLEncoded
    }

    private static func challenge(for verifier: String) -> String {
        Data(SHA256.hash(data: Data(verifier.utf8))).base64URLEncoded
    }
}

extension Auth: ASWebAuthenticationPresentationContextProviding {
    nonisolated func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        MainActor.assumeIsolated { ASPresentationAnchor() }
    }
}
