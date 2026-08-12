import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var auth: Auth
    @StateObject private var chat: ChatModel
    @StateObject private var conversations: ConversationsModel
    @State private var draft = ""
    @State private var signingIn = false
    @State private var signInError: String?
    @State private var showingConversations = false

    init(chat: ChatModel, conversations: ConversationsModel) {
        _chat = StateObject(wrappedValue: chat)
        _conversations = StateObject(wrappedValue: conversations)
    }

    var body: some View {
        Group {
            if auth.isSignedIn {
                conversation
                    .task { await chat.restoreThread() }
                    .sheet(isPresented: $showingConversations) { conversationsSheet }
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

    private var conversationsSheet: some View {
        NavigationStack {
            List {
                Button {
                    chat.startNew()
                    showingConversations = false
                } label: {
                    Label("Nueva conversación", systemImage: "square.and.pencil")
                        .frame(minHeight: 44)
                }
                ForEach(conversations.summaries) { summary in
                    Button {
                        Task {
                            await chat.open(summary.id)
                            showingConversations = false
                        }
                    } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(summary.title).font(.body)
                            if let preview = summary.preview, !preview.isEmpty {
                                Text(preview)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                        }
                        .frame(minHeight: 44, alignment: .leading)
                    }
                }
            }
            .navigationTitle("Conversaciones")
            .task { await conversations.refresh() }
        }
    }

    private var conversation: some View {
        VStack(spacing: 0) {
            HStack {
                Button {
                    showingConversations = true
                } label: {
                    Image(systemName: "line.3.horizontal")
                        .frame(width: 44, height: 44)
                }
                Spacer()
                Button {
                    chat.startNew()
                } label: {
                    Image(systemName: "square.and.pencil")
                        .frame(width: 44, height: 44)
                }
            }
            .padding(.horizontal, 8)
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
