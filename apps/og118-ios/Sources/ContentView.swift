import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var auth: Auth
    @StateObject private var chat: ChatModel
    @StateObject private var conversations: ConversationsModel
    @StateObject private var catalog: CatalogModel
    @State private var draft = ""
    @State private var signingIn = false
    @State private var signInError: String?
    @State private var showingConversations = false
    @State private var showingContext = false

    init(chat: ChatModel, conversations: ConversationsModel, catalog: CatalogModel) {
        _chat = StateObject(wrappedValue: chat)
        _conversations = StateObject(wrappedValue: conversations)
        _catalog = StateObject(wrappedValue: catalog)
    }

    var body: some View {
        ZStack {
            GlassBackground()
            if auth.isSignedIn {
                conversation
                    .task { await chat.restoreThread() }
                    .sheet(isPresented: $showingConversations) { conversationsSheet }
                    .sheet(isPresented: $showingContext) { contextSheet }
                    .task { await catalog.refresh() }
            } else {
                signIn
            }
        }
        .preferredColorScheme(.dark)
        .tint(Theme.accent)
    }

    private var signIn: some View {
        VStack(spacing: 20) {
            Text("og118")
                .font(.largeTitle.bold())
                .foregroundStyle(Theme.text)
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

    private var contextSheet: some View {
        NavigationStack {
            List {
                Section("Elemento") {
                    contextRow(titulo: "og118 (base)", activo: chat.element == nil) {
                        chat.element = nil
                    }
                    ForEach(catalog.elements) { elemento in
                        contextRow(
                            titulo: elemento.displayLabel,
                            activo: chat.element == elemento.token
                        ) { chat.element = elemento.token }
                    }
                }
                Section("Proyecto") {
                    contextRow(titulo: "Sin proyecto", activo: chat.corpusID == nil) {
                        chat.corpusID = nil
                    }
                    ForEach(catalog.projects) { proyecto in
                        contextRow(titulo: proyecto.name, activo: chat.corpusID == proyecto.id) {
                            chat.corpusID = proyecto.id
                        }
                    }
                }
            }
            .navigationTitle("Contexto del turno")
        }
    }

    private func contextRow(
        titulo: String,
        activo: Bool,
        accion: @escaping () -> Void
    ) -> some View {
        Button {
            accion()
            showingContext = false
        } label: {
            HStack {
                Text(titulo)
                Spacer()
                if activo {
                    Image(systemName: "checkmark").foregroundStyle(Theme.accent)
                }
            }
            .frame(minHeight: 44)
        }
    }

    private var conversation: some View {
        VStack(spacing: 0) {
            HStack {
                Button {
                    showingConversations = true
                } label: {
                    Image(systemName: "line.3.horizontal")
                        .foregroundStyle(Theme.textMuted)
                        .frame(width: 44, height: 44)
                }
                Spacer()
                Button {
                    showingContext = true
                } label: {
                    VStack(spacing: 1) {
                        Text(catalog.elementName(for: chat.element))
                            .font(.footnote.weight(.semibold))
                            .foregroundStyle(Theme.accent)
                        if let proyecto = catalog.projectName(for: chat.corpusID) {
                            Text(proyecto)
                                .font(.caption2)
                                .foregroundStyle(Theme.textMuted)
                        }
                    }
                    .frame(minHeight: 44)
                }
                Spacer()
                Button {
                    chat.startNew()
                } label: {
                    Image(systemName: "square.and.pencil")
                        .foregroundStyle(Theme.textMuted)
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
                            .foregroundStyle(Theme.danger)
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
                .foregroundStyle(role == .user ? Theme.accent : Theme.textMuted)
            Text(text)
                .font(.body)
                .foregroundStyle(Theme.text)
                .textSelection(.enabled)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.vertical, 10)
        .padding(.horizontal, 14)
        .background(role == .user ? Theme.bubbleUser : Theme.bubbleAssistant)
        .clipShape(RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(role == .user ? Theme.bubbleUserBorder : Theme.bubbleBorder, lineWidth: 1)
        )
    }

    private var composer: some View {
        HStack(spacing: 8) {
            TextField("Escribe…", text: $draft, axis: .vertical)
                .lineLimit(1...5)
                .textFieldStyle(.plain)
                .foregroundStyle(Theme.text)
                .padding(.vertical, 10)
                .padding(.horizontal, 14)
                .background(Theme.surface)
                .clipShape(RoundedRectangle(cornerRadius: Theme.radius))
                .overlay(
                    RoundedRectangle(cornerRadius: Theme.radius)
                        .stroke(Theme.surfaceBorder, lineWidth: 1)
                )
            Button {
                chat.send(draft)
                draft = ""
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.title2)
                    .foregroundStyle(Theme.accent)
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
