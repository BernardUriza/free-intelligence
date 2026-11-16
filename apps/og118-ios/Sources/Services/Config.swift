import Foundation

enum Config {
    static let apiBase = URL(string: "https://og118-api.thankfulmoss-53b8b5c9.eastus2.azurecontainerapps.io")!
    static let auth0Domain = "dev-1r4daup7ofj7q6gn.us.auth0.com"
    static let auth0Audience = "https://api.og118.ai"
    static let auth0Scope = "openid profile email offline_access"
    static let bundleIdentifier = "com.bernard.og118"
    static let callbackScheme = "com.bernard.og118"

    static var auth0ClientID: String {
        (Bundle.main.object(forInfoDictionaryKey: "OG118Auth0ClientID") as? String) ?? ""
    }

    /// Viaja en cada petición: los logs del servidor dicen qué build sigue vivo.
    static var clienteID: String {
        let info = Bundle.main.infoDictionary
        let corta = info?["CFBundleShortVersionString"] as? String ?? "?"
        let build = info?["CFBundleVersion"] as? String ?? "?"
        return "ios/\(corta)(\(build))"
    }

    static var redirectURI: String {
        "\(callbackScheme)://\(auth0Domain)/ios/\(bundleIdentifier)/callback"
    }
}
