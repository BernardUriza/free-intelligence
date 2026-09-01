import Foundation

enum Sitio {
    static let inicio = URL(string: "https://www.theblowers.com/")!
    static let login = URL(string: "https://www.theblowers.com/en/login")!
    static let dominios = ["theblowers.com", "lespompeurs.com"]

    static func esDelSitio(_ url: URL) -> Bool {
        guard let host = url.host?.lowercased() else { return false }
        return dominios.contains { host == $0 || host.hasSuffix("." + $0) }
    }
}

enum UltimaPagina {
    private static let clave = "theblowers.ultima-pagina"

    static func guardar(_ url: URL) {
        guard Sitio.esDelSitio(url) else { return }
        UserDefaults.standard.set(url.absoluteString, forKey: clave)
    }

    static func recuperar() -> URL {
        guard let guardada = UserDefaults.standard.string(forKey: clave),
              let url = URL(string: guardada),
              Sitio.esDelSitio(url) else { return Sitio.inicio }
        return url
    }
}
