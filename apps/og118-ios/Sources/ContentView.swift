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
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// Mismo contrato que fi-glass: 0.3s ease-out, y NADA si el usuario pidió
    /// movimiento reducido (`prefers-reduced-motion`).
    private var aparicion: Animation? {
        reduceMotion ? nil : .easeOut(duration: 0.3)
    }

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
                        // La hoja se cierra PRIMERO: si se espera a la red, el
                        // cambio ocurre oculto detrás y el usuario no ve nada.
                        showingConversations = false
                        Task { await chat.open(summary.id) }
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
            encabezado
            ZStack {
                if chat.messages.isEmpty && !chat.isStreaming {
                    estadoVacio.transition(.opacity)
                } else {
                    transcript.transition(.opacity)
                }
            }
            .id(chat.conversationID)
            .animation(aparicion, value: chat.conversationID)
            .animation(aparicion, value: chat.messages.isEmpty)
            composer
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }

    private var encabezado: some View {
        HStack(spacing: 4) {
            Button { showingConversations = true } label: {
                Image(systemName: "line.3.horizontal")
                    .font(.system(size: 17, weight: .medium))
                    .foregroundStyle(Theme.textMuted)
                    .frame(width: 44, height: 44)
            }
            Spacer(minLength: 0)
            Button { showingContext = true } label: {
                HStack(spacing: 6) {
                    Circle().fill(Theme.accent).frame(width: 7, height: 7)
                    VStack(spacing: 0) {
                        Text(catalog.elementName(for: chat.element))
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(Theme.text)
                        if let proyecto = catalog.projectName(for: chat.corpusID) {
                            Text(proyecto)
                                .font(.caption2)
                                .foregroundStyle(Theme.textMuted)
                        }
                    }
                    Image(systemName: "chevron.down")
                        .font(.system(size: 10, weight: .semibold))
                        .foregroundStyle(Theme.textMuted)
                }
                .frame(minHeight: 44)
                .contentTransition(.opacity)
                .animation(aparicion, value: chat.element)
                .animation(aparicion, value: chat.corpusID)
            }
            Spacer(minLength: 0)
            Button { chat.startNew() } label: {
                Image(systemName: "square.and.pencil")
                    .font(.system(size: 17, weight: .medium))
                    .foregroundStyle(Theme.textMuted)
                    .frame(width: 44, height: 44)
            }
        }
        .padding(.horizontal, 6)
        .overlay(alignment: .bottom) {
            Rectangle().fill(Theme.surfaceBorder).frame(height: 0.5)
        }
    }

    private var estadoVacio: some View {
        VStack(spacing: 10) {
            Spacer()
            Text("og118")
                .font(.system(size: 34, weight: .bold))
                .foregroundStyle(Theme.text)
            Text("Pregunta lo que sea.")
                .font(.subheadline)
                .foregroundStyle(Theme.textMuted)
            Spacer()
        }
        .frame(maxWidth: .infinity)
    }

    private var transcript: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 14) {
                    ForEach(chat.messages) { message in
                        MessageBubble(
                            role: message.role,
                            text: message.content,
                            author: message.author
                        )
                        .transition(.opacity.combined(with: .move(edge: .bottom)))
                    }
                    if chat.isStreaming {
                        if chat.liveText.isEmpty {
                            HStack {
                                TypingIndicator()
                                Spacer()
                            }
                            .padding(.leading, 14)
                            .transition(.opacity)
                        } else {
                            MessageBubble(
                                role: .assistant,
                                text: chat.liveText,
                                author: chat.liveAuthor
                            )
                        }
                    }
                    if let error = chat.errorMessage {
                        Text(error)
                            .font(.footnote)
                            .foregroundStyle(Theme.danger)
                            .padding(.horizontal, 14)
                    }
                    Color.clear.frame(height: 1).id("fondo")
                }
                .padding(.horizontal, 12)
                .padding(.top, 14)
                .animation(aparicion, value: chat.messages.count)
                .animation(aparicion, value: chat.isStreaming)
            }
            .onChange(of: chat.messages.count) { _, _ in
                withAnimation { proxy.scrollTo("fondo", anchor: .bottom) }
            }
            .onChange(of: chat.liveText) { _, _ in
                proxy.scrollTo("fondo", anchor: .bottom)
            }
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

    private var puedeEnviar: Bool {
        !draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !chat.isStreaming
    }

    private var composer: some View {
        HStack(alignment: .bottom, spacing: 2) {
            TextField("Escribe…", text: $draft, axis: .vertical)
                .lineLimit(1...5)
                .textFieldStyle(.plain)
                .font(.body)
                .foregroundStyle(Theme.text)
                .padding(.leading, 16)
                .padding(.vertical, 12)
            if chat.isStreaming {
                Button { chat.cancel() } label: {
                    Image(systemName: "stop.circle.fill")
                        .font(.system(size: 27))
                        .foregroundStyle(Theme.textMuted)
                        .frame(width: 44, height: 44)
                }
            } else {
                Button {
                    chat.send(draft)
                    draft = ""
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 27))
                        .foregroundStyle(puedeEnviar ? Theme.accent : Theme.textMuted.opacity(0.4))
                        .frame(width: 44, height: 44)
                }
                .disabled(!puedeEnviar)
            }
        }
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 24))
        .overlay(
            RoundedRectangle(cornerRadius: 24).stroke(Theme.surfaceBorder, lineWidth: 1)
        )
        .padding(.horizontal, 12)
        .padding(.bottom, 8)
        .padding(.top, 6)
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
