import Foundation
import WebKit

/// La sesión persiste, así que esto casi nunca corre. Cuando el sitio la tira,
/// el teléfono no debe pedirle a Bernard que escriba nada: la app se reautentica
/// sola con la credencial que trae dentro.
enum AutoLogin {
    /// Sin tope, un password rechazado convierte la app en un bucle de reintentos
    /// contra el servidor del sitio.
    private static let intentosMaximos = 2
    private static var intentos = 0

    static func esPantallaDeLogin(_ url: URL?) -> Bool {
        guard let ruta = url?.path.lowercased() else { return false }
        return ruta.contains("/login")
    }

    /// El sitio sirve la portada con contenido público aunque no haya sesión, así
    /// que "cargó bien" no significa "está autenticado": hay que preguntarlo.
    static func asegurarSesion(en web: WKWebView) {
        guard Credencial.completa, intentos < intentosMaximos else { return }
        web.evaluateJavaScript(Self.guionDeEstado) { resultado, _ in
            guard let estado = resultado as? String else { return }
            if estado == "autenticado" {
                intentos = 0
                print("[login] sesion viva")
            } else {
                intentos += 1
                print("[login] sin sesion (intento \(intentos)) - voy a /en/login")
                web.load(URLRequest(url: Sitio.login))
            }
        }
    }

    static func intentar(en web: WKWebView, motivo: String) {
        guard let correo = Credencial.correo, let password = Credencial.password else {
            print("[login] sin credencial embebida - \(motivo)")
            return
        }
        web.evaluateJavaScript(guion(correo: correo, password: password)) { resultado, error in
            if let error {
                print("[login] fallo la inyeccion: \(error.localizedDescription)")
            } else {
                print("[login] \(motivo) -> \(resultado ?? "sin resultado")")
            }
        }
    }

    private static let guionDeEstado = [
        "(function () {",
        "  var enlaces = Array.prototype.slice.call(document.querySelectorAll('a'));",
        "  var salir = enlaces.some(function (a) { return /disconnect|log ?out/i.test(a.href + ' ' + a.textContent); });",
        "  return salir ? 'autenticado' : 'anonimo';",
        "})();"
    ].joined(separator: "\n")

    private static func guion(correo: String, password: String) -> String {
        [
            "(function () {",
            "  var f = document.querySelector('#connection_form');",
            "  if (!f) { return 'sin-formulario'; }",
            "  var correo = f.querySelector('input[name=email]');",
            "  var clave = f.querySelector('input[name=password]');",
            "  if (!correo || !clave) { return 'sin-campos'; }",
            "  if (clave.value) { return 'ya-tenia-valor'; }",
            "  var poner = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;",
            "  poner.call(correo, " + literal(correo) + ");",
            "  correo.dispatchEvent(new Event('input', { bubbles: true }));",
            "  poner.call(clave, " + literal(password) + ");",
            "  clave.dispatchEvent(new Event('input', { bubbles: true }));",
            "  clave.dispatchEvent(new Event('change', { bubbles: true }));",
            "  var enviar = f.querySelector('input[type=submit], button[type=submit]');",
            "  if (enviar) { enviar.click(); } else { f.submit(); }",
            "  return 'enviado';",
            "})();"
        ].joined(separator: "\n")
    }

    private static func literal(_ valor: String) -> String {
        let datos = try! JSONSerialization.data(withJSONObject: [valor])
        let arreglo = String(data: datos, encoding: .utf8)!
        return String(arreglo.dropFirst().dropLast())
    }
}
