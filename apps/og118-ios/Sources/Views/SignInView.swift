import SwiftUI

/// La puerta de entrada: wordmark + botón de Auth0. El error de login se
/// pinta aquí mismo, no en un alert, para que sobreviva a la vuelta del
/// browser de PKCE.
struct SignInView: View {
    @EnvironmentObject private var auth: Auth
    @State private var signingIn = false
    @State private var signInError: String?

    var body: some View {
        VStack(spacing: 20) {
            Wordmark(size: 34)
            Text("Inicia sesión para continuar.")
                .foregroundStyle(Theme.textMuted)
            Button {
                Task { await startSignIn() }
            } label: {
                Text(signingIn ? "Abriendo…" : "Iniciar sesión")
                    .frame(maxWidth: 220)
            }
            .buttonStyle(AccentButtonStyle())
            .disabled(signingIn)
            if let signInError {
                Text(signInError)
                    .font(.footnote)
                    .foregroundStyle(Theme.danger)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func startSignIn() async {
        signingIn = true
        signInError = nil
        do {
            try await auth.signIn()
        } catch {
            signInError = error.localizedDescription
        }
        signingIn = false
    }
}
