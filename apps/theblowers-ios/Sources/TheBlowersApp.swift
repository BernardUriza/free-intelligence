import SwiftUI

@main
struct TheBlowersApp: App {
    @Environment(\.scenePhase) private var fase

    var body: some Scene {
        WindowGroup {
            ZStack {
                Color.black.ignoresSafeArea()
                NavegadorDelSitio()
                    .ignoresSafeArea(.container, edges: .bottom)
                // El app switcher fotografía la pantalla: sin esta cortina, el
                // último contenido queda visible para quien tome el teléfono.
                if fase != .active {
                    Cortina().transition(.opacity)
                }
            }
            .preferredColorScheme(.dark)
        }
    }
}

private struct Cortina: View {
    var body: some View {
        ZStack {
            Color(red: 0.72, green: 0.02, blue: 0.02).ignoresSafeArea()
            Image("AppIcon")
                .resizable()
                .scaledToFit()
                .frame(width: 96, height: 96)
                .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                .opacity(0.9)
        }
    }
}
