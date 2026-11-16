import Foundation
import UserNotifications
#if canImport(UIKit)
import UIKit
#endif

/// El aviso de «ya te contestaron». Dos caminos, nunca los dos a la vez: si el
/// turno termina con la app todavía viva en segundo plano, el aviso es local;
/// si iOS ya la suspendió, el servidor termina el turno y manda el push.
@MainActor
final class Avisos: NSObject, ObservableObject, UNUserNotificationCenterDelegate {
    static let shared = Avisos()

    @Published private(set) var tokenDispositivo: String?
    @Published var hiloPorAbrir: String?
    /// Llegó un push con la app abierta: el hilo se relee en vez de avisar.
    @Published private(set) var llegadas = 0

    private static let pedidoKey = "og118.avisos.pedido"
    nonisolated static let llaveDeHilo = "conversation_id"

    #if DEBUG
    static let ambiente = "development"
    #else
    static let ambiente = "production"
    #endif

    func instalar() {
        UNUserNotificationCenter.current().delegate = self
        Task { await registrarSiYaHayPermiso() }
    }

    /// Se pide al mandar el primer mensaje, no al abrir la app: ahí es cuando
    /// la pregunta «¿te aviso cuando conteste?» tiene sentido.
    func pedirPermisoUnaVez(defaults: UserDefaults = .standard) {
        guard !defaults.bool(forKey: Self.pedidoKey) else { return }
        defaults.set(true, forKey: Self.pedidoKey)
        Task {
            let concedido = (try? await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .sound, .badge])) ?? false
            if concedido { registrar() }
        }
    }

    private func registrarSiYaHayPermiso() async {
        let estado = await UNUserNotificationCenter.current().notificationSettings().authorizationStatus
        if estado == .authorized || estado == .provisional { registrar() }
    }

    private func registrar() {
        #if canImport(UIKit)
        UIApplication.shared.registerForRemoteNotifications()
        #endif
    }

    func tokenRecibido(_ datos: Data) {
        tokenDispositivo = datos.map { String(format: "%02x", $0) }.joined()
    }

    func avisarLocal(titulo: String, cuerpo: String, hilo: String) {
        let contenido = UNMutableNotificationContent()
        contenido.title = titulo
        contenido.body = Self.recortar(cuerpo)
        contenido.sound = .default
        contenido.threadIdentifier = hilo
        contenido.userInfo = [Self.llaveDeHilo: hilo]
        UNUserNotificationCenter.current().add(
            UNNotificationRequest(identifier: UUID().uuidString, content: contenido, trigger: nil)
        )
    }

    static func recortar(_ texto: String, tope: Int = 160) -> String {
        let plano = texto.split(whereSeparator: \.isWhitespace).joined(separator: " ")
        return plano.count <= tope ? plano : String(plano.prefix(tope - 1)) + "…"
    }

    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification
    ) async -> UNNotificationPresentationOptions {
        await MainActor.run { llegadas += 1 }
        return []
    }

    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse
    ) async {
        let hilo = response.notification.request.content.userInfo[Self.llaveDeHilo] as? String
        await MainActor.run { hiloPorAbrir = hilo }
    }
}
