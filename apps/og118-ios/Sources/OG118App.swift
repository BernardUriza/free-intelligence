import SwiftUI

@main
struct OG118App: App {
    @StateObject private var auth = Auth()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(auth)
        }
    }
}

private struct RootView: View {
    @EnvironmentObject private var auth: Auth

    var body: some View {
        let diag = TurnDiagnostics()
        let client = Og118Client(accessToken: { try await auth.token() }, diagnostico: diag)
        let chat = ChatModel(client: client)
        let voz = VoiceModel(client: client)
        return ContentView(
            chat: chat,
            conversations: ConversationsModel(client: client),
            catalog: CatalogModel(client: client),
            voz: voz,
            llamada: ResonanceCallModel(chat: chat, client: client) { voz.errorMessage = $0 },
            diagnostico: diag
        )
    }
}
