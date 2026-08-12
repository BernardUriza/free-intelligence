import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var auth: Auth
    @StateObject private var chat: ChatModel
    @State private var draft = ""
    @State private var signingIn = false
    @State private var signInError: String?

    init(chat: ChatModel) {
        _chat = StateObject(wrappedValue: chat)
    }

    var body: some View {
        Group {
            if auth.isSignedIn {
                conversation
            } else {
                signIn
            }
        }
    }

    private var signIn: some View {
        VStack(spacing: 20) {
            Text("og118")
                .font(.largeTitle.bold())
            Text("Inicia sesión para continuar.")
                .foregroundStyle(.secondary)
            Button {
                Task { await startSignIn() }
            } label: {
                Text(signingIn ? "Abriendo…" : "Iniciar sesión")
                    .frame(maxWidth: 260, minHeight: 50)
            }
            .buttonStyle(.borderedProminent)
            .disabled(signingIn)
            if let signInError {
                Text(signInError)
                    .font(.footnote)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var conversation: some View {
        VStack(spacing: 0) {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    ForEach(chat.messages) { message in
                        bubble(role: message.role, text: message.content, author: message.author)
                    }
                    if chat.isStreaming {
                        bubble(
                            role: .assistant,
                            text: chat.liveText.isEmpty ? "…" : chat.liveText,
                            author: chat.liveAuthor
                        )
                    }
                    if let error = chat.errorMessage {
                        Text(error)
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }
                }
                .padding(12)
            }
            composer
        }
    }

    private func bubble(role: ChatMessage.Role, text: String, author: String?) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(role == .user ? "Tú" : (author ?? "og118"))
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(text)
                .font(.body)
                .textSelection(.enabled)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 10)
        .padding(.horizontal, 14)
        .background(role == .user ? Color.secondary.opacity(0.12) : Color.clear)
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }

    private var composer: some View {
        HStack(spacing: 8) {
            TextField("Escribe…", text: $draft, axis: .vertical)
                .lineLimit(1...5)
                .textFieldStyle(.roundedBorder)
            Button {
                chat.send(draft)
                draft = ""
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.title2)
                    .frame(width: 44, height: 44)
            }
            .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || chat.isStreaming)
        }
        .padding(12)
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
