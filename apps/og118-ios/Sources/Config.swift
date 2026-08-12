import Foundation

enum Config {
    static let apiBase = URL(string: "https://og118-api.thankfulmoss-53b8b5c9.eastus2.azurecontainerapps.io")!
    static let auth0Domain = "dev-1r4daup7ofj7q6gn.us.auth0.com"
    static let auth0Audience = "https://api.og118.ai"
    static let auth0Scope = "openid profile email offline_access"
    static let bundleIdentifier = "ai.og118.app"
    static let callbackScheme = "og118"

    static var auth0ClientID: String {
        (Bundle.main.object(forInfoDictionaryKey: "OG118Auth0ClientID") as? String) ?? ""
    }

    static var redirectURI: String {
        "\(callbackScheme)://\(auth0Domain)/ios/\(bundleIdentifier)/callback"
    }
}
