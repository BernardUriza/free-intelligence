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
        return ContentView(
            chat: ChatModel(client: client),
            conversations: ConversationsModel(client: client),
            catalog: CatalogModel(client: client),
            voz: VoiceModel(client: client),
            diagnostico: diag
        )
    }
}
