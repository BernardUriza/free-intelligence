import SwiftUI

private let formatoISO: ISO8601DateFormatter = {
    let f = ISO8601DateFormatter()
    f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    return f
}()

private let formatoISOSimple: ISO8601DateFormatter = {
    let f = ISO8601DateFormatter()
    f.formatOptions = [.withInternetDateTime]
    return f
}()

/// Hora del sidebar, fija en es-MX 24h igual que la web (B3-OG118-5): la UI es
/// en español, así que la fecha no sigue el locale del sistema.
private let formatoHoraCorta: DateFormatter = {
    let f = DateFormatter()
    f.locale = Locale(identifier: "es_MX")
    f.dateFormat = "d MMM HH:mm"
    return f
}()

func horaCorta(_ iso: String) -> String {
    guard let fecha = formatoISO.date(from: iso) ?? formatoISOSimple.date(from: iso) else {
        return ""
    }
    return formatoHoraCorta.string(from: fecha)
}

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
    @State private var busqueda = ""
    @State private var mostrarArchivados = false
    @State private var renombrando: ConversationSummary?
    @State private var nuevoNombre = ""
    @State private var borrando: ConversationSummary?
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
            wordmark(size: 34)
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

    private func wordmark(size: CGFloat) -> Text {
        Text("og118")
            .font(.system(size: size, weight: .bold))
            .foregroundStyle(Theme.text)
        + Text(".ai")
            .font(.system(size: size, weight: .bold))
            .foregroundStyle(Theme.accent)
    }

    // MARK: - Conversaciones (el sidebar de la web, como hoja)

    private func coincide(_ summary: ConversationSummary) -> Bool {
        let q = busqueda
            .folding(options: [.diacriticInsensitive, .caseInsensitive], locale: .current)
            .trimmingCharacters(in: .whitespaces)
        guard !q.isEmpty else { return true }
        let titulo = summary.title
            .folding(options: [.diacriticInsensitive, .caseInsensitive], locale: .current)
        let preview = (summary.preview ?? "")
            .folding(options: [.diacriticInsensitive, .caseInsensitive], locale: .current)
        return titulo.contains(q) || preview.contains(q)
    }

    private var conversationsSheet: some View {
        NavigationStack {
            List {
                Section {
                    Button {
                        chat.startNew()
                        showingConversations = false
                    } label: {
                        Label("Nuevo chat", systemImage: "square.and.pencil")
                            .foregroundStyle(Theme.accent)
                            .frame(minHeight: 44)
                    }
                }

                let fijados = conversations.pinned.filter(coincide)
                let activos = conversations.active.filter(coincide)
                let archivados = conversations.archived.filter(coincide)

                if !fijados.isEmpty {
                    Section("Fijados") {
                        ForEach(fijados) { chatRow($0, fijado: true) }
                    }
                }
                if !activos.isEmpty {
                    Section("Chats") {
                        ForEach(activos) { chatRow($0, fijado: false) }
                    }
                }
                if !archivados.isEmpty {
                    Section {
                        // La búsqueda le gana al colapso, igual que la web: un
                        // match archivado debe VERSE, no quedar tras el toggle.
                        DisclosureGroup(
                            isExpanded: Binding(
                                get: { mostrarArchivados || !busqueda.isEmpty },
                                set: { mostrarArchivados = $0 }
                            )
                        ) {
                            ForEach(archivados) { archivedRow($0) }
                        } label: {
                            Text("Archivados (\(archivados.count))")
                                .foregroundStyle(Theme.textMuted)
                        }
                    }
                }

                Section {
                } footer: {
                    Text("Sincronizado en tu cuenta — disponible en todos tus dispositivos.")
                }
            }
            .searchable(text: $busqueda, prompt: "Buscar chats…")
            .navigationTitle("Conversaciones")
            .navigationBarTitleDisplayMode(.inline)
            .task { await conversations.refresh() }
            .alert("Renombrar chat", isPresented: renombrandoActivo) {
                TextField("Nombre del chat", text: $nuevoNombre)
                Button("Guardar") {
                    guard let objetivo = renombrando else { return }
                    let nombre = nuevoNombre
                    renombrando = nil
                    Task { adopt(await conversations.rename(objetivo.id, to: nombre)) }
                }
                Button("Cancelar", role: .cancel) { renombrando = nil }
            } message: {
                Text("Deja el nombre vacío para volver al título automático.")
            }
            .confirmationDialog(
                "¿Borrar «\(borrando?.title ?? "")»? Se borra de tu cuenta en todos tus dispositivos.",
                isPresented: borrandoActivo,
                titleVisibility: .visible
            ) {
                Button("Borrar chat", role: .destructive) {
                    guard let objetivo = borrando else { return }
                    borrando = nil
                    Task {
                        await conversations.delete(objetivo.id)
                        if objetivo.id == chat.conversationID {
                            chat.startNew()
                        }
                    }
                }
                Button("Cancelar", role: .cancel) { borrando = nil }
            }
        }
    }

    private var renombrandoActivo: Binding<Bool> {
        Binding(get: { renombrando != nil }, set: { if !$0 { renombrando = nil } })
    }

    private var borrandoActivo: Binding<Bool> {
        Binding(get: { borrando != nil }, set: { if !$0 { borrando = nil } })
    }

    /// Un pin/rename/archivado sobre la conversación ABIERTA reemplaza su
    /// record; el ChatModel debe partir de esa versión en el próximo save.
    private func adopt(_ record: ConversationRecord?) {
        if let record { chat.adoptBase(record) }
    }

    private func resumenFila(_ summary: ConversationSummary) -> some View {
        HStack(alignment: .top, spacing: 8) {
            VStack(alignment: .leading, spacing: 2) {
                Text(summary.title)
                    .font(.body)
                    .foregroundStyle(Theme.text)
                    .lineLimit(1)
                if let preview = summary.preview, !preview.isEmpty {
                    Text(preview)
                        .font(.caption)
                        .foregroundStyle(Theme.textMuted)
                        .lineLimit(1)
                }
            }
            Spacer(minLength: 4)
            Text(horaCorta(summary.updatedAt))
                .font(.caption2)
                .foregroundStyle(Theme.textFaint)
                .monospacedDigit()
        }
        .frame(minHeight: 44)
    }

    private func chatRow(_ summary: ConversationSummary, fijado: Bool) -> some View {
        Button {
            // La hoja se cierra PRIMERO: si se espera a la red, el cambio
            // ocurre oculto detrás y el usuario no ve nada.
            showingConversations = false
            Task { await chat.open(summary.id) }
        } label: {
            resumenFila(summary)
        }
        .swipeActions(edge: .leading, allowsFullSwipe: true) {
            Button {
                Task { adopt(await conversations.setPinned(summary.id, !fijado)) }
            } label: {
                Label(fijado ? "Desfijar" : "Fijar", systemImage: fijado ? "pin.slash" : "pin")
            }
            .tint(Theme.accentDeep)
        }
        .swipeActions(edge: .trailing) {
            Button {
                Task { adopt(await conversations.setArchived(summary.id, true)) }
            } label: {
                Label("Archivar", systemImage: "archivebox")
            }
            .tint(Color(hex: 0x475569))
        }
        .contextMenu {
            Button {
                renombrando = summary
                nuevoNombre = summary.title
            } label: {
                Label("Renombrar chat", systemImage: "pencil")
            }
            Button {
                Task { adopt(await conversations.setPinned(summary.id, !fijado)) }
            } label: {
                Label(fijado ? "Desfijar chat" : "Fijar chat", systemImage: fijado ? "pin.slash" : "pin")
            }
            Button {
                Task { adopt(await conversations.setArchived(summary.id, true)) }
            } label: {
                Label("Archivar chat", systemImage: "archivebox")
            }
        }
    }

    /// Archivar es la ruta amable; el borrado destructivo vive SOLO aquí,
    /// dentro de Archivados, igual que en la web.
    private func archivedRow(_ summary: ConversationSummary) -> some View {
        Button {
            showingConversations = false
            Task { await chat.open(summary.id) }
        } label: {
            resumenFila(summary)
        }
        .swipeActions(edge: .leading, allowsFullSwipe: true) {
            Button {
                Task { adopt(await conversations.setArchived(summary.id, false)) }
            } label: {
                Label("Restaurar", systemImage: "arrow.uturn.backward")
            }
            .tint(Theme.accentDeep)
        }
        .swipeActions(edge: .trailing) {
            Button(role: .destructive) {
                borrando = summary
            } label: {
                Label("Borrar", systemImage: "trash")
            }
        }
    }

    // MARK: - Contexto del turno (elemento + proyecto)

    private var contextSheet: some View {
        NavigationStack {
            List {
                Section("Elemento") {
                    elementRow(elemento: nil)
                    ForEach(catalog.elements) { elementRow(elemento: $0) }
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
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func chipEngine(_ engine: String) -> some View {
        Text(engine)
            .font(.system(size: 10, design: .monospaced))
            .foregroundStyle(Theme.badgeSelectedText)
            .padding(.horizontal, 5)
            .padding(.vertical, 2)
            .background(Color(hex: 0x10B981).opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 4))
            .overlay(
                RoundedRectangle(cornerRadius: 4).stroke(Theme.chipBorder, lineWidth: 1)
            )
    }

    /// La fila rica del selector web: badge atómico, nombre, chip del engine y
    /// descripción de la persona.
    private func elementRow(elemento: Element?) -> some View {
        let activo = chat.element == elemento?.token
        return Button {
            chat.element = elemento?.token
            showingContext = false
        } label: {
            HStack(alignment: .center, spacing: 9) {
                AtomicBadge(elemento: elemento, activo: activo)
                VStack(alignment: .leading, spacing: 2) {
                    Text(elemento?.displayName ?? "og118 (base)")
                        .font(.body)
                        .foregroundStyle(Theme.text)
                    if let descripcion = elemento?.description, !descripcion.isEmpty {
                        Text(descripcion)
                            .font(.caption)
                            .foregroundStyle(Theme.textMuted)
                            .lineLimit(2)
                    }
                }
                Spacer()
                if let engine = elemento?.engine, !engine.isEmpty {
                    chipEngine(engine)
                }
                if activo {
                    Image(systemName: "checkmark").foregroundStyle(Theme.accent)
                }
            }
            .frame(minHeight: 44)
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

    // MARK: - Conversación

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
            wordmark(size: 16)
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

    /// La tarjeta de arranque de la web (`Og118StartScreen`): casilla del
    /// oganesón, wordmark, y el mismo copy sobre vidrio.
    private var estadoVacio: some View {
        VStack {
            Spacer()
            VStack(spacing: 14) {
                VStack(spacing: 2) {
                    Text("118")
                        .font(.system(size: 12, weight: .medium, design: .monospaced))
                        .foregroundStyle(Theme.textMuted)
                    Text("Og")
                        .font(.system(size: 34, weight: .bold))
                        .foregroundStyle(Theme.accent)
                    Text("Oganesson")
                        .font(.system(size: 10))
                        .foregroundStyle(Theme.textMuted)
                }
                .frame(width: 88, height: 88)
                .background(Color.white.opacity(0.04))
                .clipShape(RoundedRectangle(cornerRadius: 14))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Theme.accent.opacity(0.35), lineWidth: 1)
                )
                .shadow(color: Theme.accent.opacity(0.15), radius: 16, y: 8)

                wordmark(size: 30)

                Text("Og · 118 · Oganesson — synthetic, the heaviest known, the end of the table.")
                    .font(.footnote)
                    .foregroundStyle(Theme.textMuted)
                    .multilineTextAlignment(.center)

                Text("A personal thinking companion on the Free Intelligence substrate. Glass-box by design — you see the reasoning, not just the answer.")
                    .font(.subheadline)
                    .foregroundStyle(Theme.authorName)
                    .multilineTextAlignment(.center)
                    .lineSpacing(3)
            }
            .padding(.vertical, 34)
            .padding(.horizontal, 26)
            .frame(maxWidth: .infinity)
            .background(Color(hex: 0x0F172A).opacity(0.55))
            .clipShape(RoundedRectangle(cornerRadius: 20))
            .overlay(
                RoundedRectangle(cornerRadius: 20)
                    .stroke(Color.white.opacity(0.18), lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.45), radius: 30, y: 20)
            .padding(.horizontal, 20)
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
                            author: message.author,
                            timestamp: message.timestamp
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

    // MARK: - Composer (vive en ComposerView; aquí sólo el cableado)

    private var elementoActivo: Element? {
        guard let token = chat.element else { return nil }
        return catalog.elements.first { $0.token == token }
    }

    private var composer: some View {
        ComposerView(
            draft: $draft,
            isStreaming: chat.isStreaming,
            elementoActivo: elementoActivo,
            tieneProyecto: chat.corpusID != nil,
            aparicion: aparicion,
            onSend: { chat.send($0) },
            onStop: { chat.cancel() },
            onOpenContext: { showingContext = true }
        )
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
