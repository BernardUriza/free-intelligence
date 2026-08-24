import SwiftUI
import WebKit

struct NavegadorDelSitio: UIViewRepresentable {
    func makeCoordinator() -> Coordinador { Coordinador() }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        // La sesión del sitio vive en el data store por defecto: es el único
        // persistente, así que cookies y localStorage sobreviven al cierre.
        config.websiteDataStore = .default()
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []

        let web = WKWebView(frame: .zero, configuration: config)
        web.navigationDelegate = context.coordinator
        web.uiDelegate = context.coordinator
        web.allowsBackForwardNavigationGestures = true
        web.scrollView.contentInsetAdjustmentBehavior = .always

        let refresco = UIRefreshControl()
        refresco.addTarget(context.coordinator,
                           action: #selector(Coordinador.recargar(_:)),
                           for: .valueChanged)
        web.scrollView.refreshControl = refresco
        context.coordinator.web = web

        web.load(URLRequest(url: UltimaPagina.recuperar()))
        return web
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    final class Coordinador: NSObject, WKNavigationDelegate, WKUIDelegate {
        weak var web: WKWebView?

        @objc func recargar(_ control: UIRefreshControl) {
            web?.reload()
        }

        func webView(_ webView: WKWebView,
                     decidePolicyFor navigationAction: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let url = navigationAction.request.url else {
                decisionHandler(.allow)
                return
            }
            if Sitio.esDelSitio(url) || url.scheme == "about" || url.scheme == "blob" || url.scheme == "data" {
                decisionHandler(.allow)
            } else {
                UIApplication.shared.open(url)
                decisionHandler(.cancel)
            }
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            webView.scrollView.refreshControl?.endRefreshing()
            if let url = webView.url { UltimaPagina.guardar(url) }
            if AutoLogin.esPantallaDeLogin(webView.url) {
                AutoLogin.intentar(en: webView, motivo: "cayo en la pantalla de login")
            } else {
                AutoLogin.asegurarSesion(en: webView)
            }
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            webView.scrollView.refreshControl?.endRefreshing()
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            webView.scrollView.refreshControl?.endRefreshing()
        }

        // target="_blank" no abre ventana en WKWebView: sin esto el enlace se pierde.
        func webView(_ webView: WKWebView,
                     createWebViewWith configuration: WKWebViewConfiguration,
                     for navigationAction: WKNavigationAction,
                     windowFeatures: WKWindowFeatures) -> WKWebView? {
            if let url = navigationAction.request.url {
                if Sitio.esDelSitio(url) {
                    webView.load(URLRequest(url: url))
                } else {
                    UIApplication.shared.open(url)
                }
            }
            return nil
        }
    }
}
