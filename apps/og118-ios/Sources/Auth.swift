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

private struct TokenResponse: Decodable {
    let accessToken: String
    let refreshToken: String?
    let expiresIn: Int?

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case expiresIn = "expires_in"
    }
}

enum AuthError: LocalizedError {
    case missingClientID
    case noCode
    case exchangeFailed(Int)
    case notSignedIn

    var errorDescription: String? {
        switch self {
        case .missingClientID:
            return "Falta el client ID de Auth0 para la app nativa."
        case .noCode:
            return "Auth0 no devolvió un código de autorización."
        case .exchangeFailed(let code):
            return "El intercambio de token falló (\(code))."
        case .notSignedIn:
            return "No hay sesión activa."
        }
    }
}

@MainActor
final class Auth: NSObject, ObservableObject {
    @Published private(set) var isSignedIn = false

    private var accessToken: String?
    private var refreshToken: String?
    private var expiresAt: Date?

    func signIn() async throws {
        let clientID = Config.auth0ClientID
        guard !clientID.isEmpty else { throw AuthError.missingClientID }

        let verifier = Self.randomVerifier()
        let callbackURL = try await authorize(clientID: clientID, verifier: verifier)

        guard
            let items = URLComponents(url: callbackURL, resolvingAgainstBaseURL: false)?.queryItems,
            let code = items.first(where: { $0.name == "code" })?.value
        else { throw AuthError.noCode }

        try await exchange(code: code, verifier: verifier, clientID: clientID)
    }

    func token() async throws -> String {
        if let accessToken, let expiresAt, expiresAt > Date().addingTimeInterval(60) {
            return accessToken
        }
        if refreshToken != nil {
            try await refresh()
            if let accessToken { return accessToken }
        }
        throw AuthError.notSignedIn
    }

    func signOut() {
        accessToken = nil
        refreshToken = nil
        expiresAt = nil
        isSignedIn = false
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

    private func exchange(code: String, verifier: String, clientID: String) async throws {
        let body = [
            "grant_type": "authorization_code",
            "client_id": clientID,
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": Config.redirectURI
        ]
        try await requestToken(body: body)
    }

    private func refresh() async throws {
        guard let refreshToken else { throw AuthError.notSignedIn }
        let body = [
            "grant_type": "refresh_token",
            "client_id": Config.auth0ClientID,
            "refresh_token": refreshToken
        ]
        try await requestToken(body: body)
    }

    private func requestToken(body: [String: String]) async throws {
        var request = URLRequest(url: URL(string: "https://\(Config.auth0Domain)/oauth/token")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw AuthError.exchangeFailed((response as? HTTPURLResponse)?.statusCode ?? 0)
        }

        let decoded = try JSONDecoder().decode(TokenResponse.self, from: data)
        accessToken = decoded.accessToken
        if let newRefresh = decoded.refreshToken { refreshToken = newRefresh }
        expiresAt = Date().addingTimeInterval(TimeInterval(decoded.expiresIn ?? 3600))
        isSignedIn = true
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
