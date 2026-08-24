import Foundation

/// El correo y el password NO viven en el repo: entran por `Config.xcconfig`
/// (gitignoreado) que se llena desde `~/.secrets/theblowers-bernard.txt`.
enum Credencial {
    static var correo: String? { leer("TheBlowersEmail") }
    static var password: String? { leer("TheBlowersPassword") }

    static var completa: Bool {
        guard let c = correo, let p = password else { return false }
        return !c.isEmpty && !p.isEmpty
    }

    private static func leer(_ clave: String) -> String? {
        guard let valor = Bundle.main.object(forInfoDictionaryKey: clave) as? String,
              !valor.isEmpty,
              !valor.hasPrefix("$(") else { return nil }
        return valor
    }
}
