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
        ContentView(chat: ChatModel(client: Og118Client(accessToken: { try await auth.token() })))
    }
}
