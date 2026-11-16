import SwiftUI

final class Delegado: NSObject, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        Task { @MainActor in Avisos.shared.instalar() }
        return true
    }

    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        Task { @MainActor in Avisos.shared.tokenRecibido(deviceToken) }
    }
}

@main
struct OG118App: App {
    @UIApplicationDelegateAdaptor(Delegado.self) private var delegado
    @StateObject private var auth: Auth
    @StateObject private var raiz: Raiz

    init() {
        let auth = Auth()
        _auth = StateObject(wrappedValue: auth)
        _raiz = StateObject(wrappedValue: Raiz(auth: auth))
    }

    var body: some Scene {
        WindowGroup {
            ContentView(
                chat: raiz.chat,
                conversations: raiz.conversations,
                catalog: raiz.catalog,
                voz: raiz.voz,
                llamada: raiz.llamada,
                diagnostico: raiz.diagnostico,
                registrarDispositivo: raiz.registrarDispositivo
            )
            .environmentObject(auth)
        }
    }
}

/// Los modelos se construyen UNA vez. Armarlos dentro de un `body` los rehacía
/// en cada cambio de `Auth` y dejaba a la bitácora en pantalla escuchando una
/// instancia que ya nadie escribía.
@MainActor
final class Raiz: ObservableObject {
    let diagnostico = TurnDiagnostics()
    let chat: ChatModel
    let conversations: ConversationsModel
    let catalog: CatalogModel
    let voz: VoiceModel
    let llamada: ResonanceCallModel
    let registrarDispositivo: (String) async -> Void

    init(auth: Auth) {
        let transporte = Transporte(
            token: { rechazado in try await auth.token(rechazado: rechazado) },
            sesionRechazada: { await auth.cerrarPorRechazo() }
        )
        let client = Og118Client(transporte: transporte, diagnostico: diagnostico)
        let chat = ChatModel(client: client)
        let voz = VoiceModel(client: client)
        self.chat = chat
        self.voz = voz
        conversations = ConversationsModel(client: client)
        catalog = CatalogModel(client: client)
        llamada = ResonanceCallModel(chat: chat, client: client) { voz.errorMessage = $0 }
        chat.alRecibirRespuesta = { respuesta, hilo in
            guard UIApplication.shared.applicationState != .active else { return }
            Avisos.shared.avisarLocal(titulo: respuesta.author?.nombre ?? "og118", cuerpo: respuesta.content, hilo: hilo)
        }
        registrarDispositivo = { token in
            try? await client.registrarDispositivo(token: token, ambiente: Avisos.ambiente)
        }
    }
}
