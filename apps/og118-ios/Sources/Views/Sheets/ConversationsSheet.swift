import SwiftUI

/// Hora del sidebar, fija en es-MX 24h igual que la web (B3-OG118-5): la UI es
/// en español, así que la fecha no sigue el locale del sistema.
private let formatoHoraCorta: DateFormatter = {
    let f = DateFormatter()
    f.locale = Locale(identifier: "es_MX")
    f.dateFormat = "d MMM HH:mm"
    return f
}()

private func horaCorta(_ iso: String) -> String {
    guard let fecha = ConversationSchema.fecha(iso) else { return "" }
    return formatoHoraCorta.string(from: fecha)
}

/// El sidebar de og118.ai como hoja, con SU anatomía — no la del `List` de
/// iOS. La versión anterior usaba `List` con `swipeActions`, que impone su
/// propio fondo, sus separadores y sus insets, y esconde toda acción tras un
/// gesto invisible. La web muestra las acciones SIEMPRE en pantallas táctiles
/// (`pointer: coarse`), y pinta cada fila sobre el fondo de cristal de la app.
struct ConversationsSheet: View {
    @ObservedObject var chat: ChatModel
    @ObservedObject var conversations: ConversationsModel
    @Environment(\.dismiss) private var dismiss

    @State private var busqueda = ""
    @State private var mostrarArchivados = false
    @State private var renombrando: ConversationSummary?
    @State private var nuevoNombre = ""
    @State private var borrando: ConversationSummary?
    @State private var esperaLarga = false

    var body: some View {
        NavigationStack {
            ZStack {
                GlassBackground()
                contenido
            }
            .navigationTitle("Conversaciones")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .automatic) {
                    Button {
                        chat.startNew()
                        dismiss()
                    } label: {
                        Label("Nuevo chat", systemImage: "square.and.pencil")
                    }
                    .tint(Theme.accent)
                }
            }
            .task {
                let aviso = Task {
                    try? await Task.sleep(nanoseconds: 3_000_000_000)
                    esperaLarga = true
                }
                await conversations.refresh()
                aviso.cancel()
                esperaLarga = false
            }
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

    private var contenido: some View {
        VStack(spacing: 0) {
            buscador
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 5) {
                    if conversations.summaries.isEmpty {
                        estadoVacio
                    }
                    if !fijados.isEmpty {
                        etiquetaGrupo("Fijados")
                        ForEach(fijados) { fila($0, fijado: true) }
                    }
                    if !activos.isEmpty {
                        etiquetaGrupo("Chats")
                        ForEach(activos) { fila($0, fijado: false) }
                    }
                    if !archivados.isEmpty { seccionArchivados }
                    if buscando, fijados.isEmpty, activos.isEmpty, archivados.isEmpty {
                        Text("Sin resultados para «\(busqueda.trimmingCharacters(in: .whitespaces))».")
                            .font(.system(size: 12.5))
                            .foregroundStyle(Theme.textFaint)
                            .padding(8)
                    }
                }
                .padding(8)
            }
            pie
        }
    }

    /// El estado vacío distingue "todavía no carga" de "no hay ninguna": sin
    /// esto, una lista que falla en silencio se ve igual que una cuenta nueva.
    @ViewBuilder
    private var estadoVacio: some View {
        VStack(alignment: .leading, spacing: 6) {
            if conversations.isLoading {
                HStack(spacing: 8) {
                    ProgressView().tint(Theme.accent)
                    Text("Cargando tus chats…")
                }
                .font(.system(size: 13))
                .foregroundStyle(Theme.textMuted)
                // El servidor duerme cuando nadie lo usa y la primera petición
                // sólo lo despierta. Callarlo hace que una espera normal se
                // sienta idéntica a una app rota — que es justo como se veía.
                if esperaLarga {
                    Text("El servidor estaba dormido; la primera carga tarda unos segundos.")
                        .font(.system(size: 12))
                        .foregroundStyle(Theme.textFaint)
                }
            } else if let error = conversations.errorMessage {
                Text(error)
                    .font(.system(size: 13))
                    .foregroundStyle(Theme.danger)
            } else {
                Text("Todavía no tienes chats guardados.")
                    .font(.system(size: 13))
                    .foregroundStyle(Theme.textMuted)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
    }

    private var buscador: some View {
        HStack(spacing: 8) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 13))
                .foregroundStyle(Theme.textFaint)
            TextField("Buscar chats…", text: $busqueda)
                .font(.system(size: 13))
                .foregroundStyle(Theme.textBody)
                .textFieldStyle(.plain)
                .autocorrectionDisabled()
            if !busqueda.isEmpty {
                Button { busqueda = "" } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundStyle(Theme.textFaint)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Limpiar búsqueda")
            }
        }
        .padding(.horizontal, 11)
        .frame(height: 38)
        .background(Theme.searchFill, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.searchBorder, lineWidth: 1))
        .padding(.horizontal, 8)
        .padding(.top, 6)
    }

    @ViewBuilder
    private var seccionArchivados: some View {
        Divider().overlay(Theme.sidebarDivider).padding(.vertical, 6)
        Button {
            mostrarArchivados.toggle()
        } label: {
            HStack {
                etiquetaGrupo("Archivados (\(archivados.count))")
                Spacer()
                Image(systemName: archivadosAbiertos ? "chevron.down" : "chevron.right")
                    .font(.system(size: 11))
                    .foregroundStyle(Theme.textFaint)
            }
            .frame(minHeight: 44)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        if archivadosAbiertos {
            ForEach(archivados) { filaArchivada($0) }
        }
    }

    private var pie: some View {
        VStack(spacing: 0) {
            Divider().overlay(Theme.sidebarDivider)
            Text("Sincronizado en tu cuenta — disponible en todos tus dispositivos.")
                .font(.system(size: 11))
                .foregroundStyle(Theme.itemMeta)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 13)
                .padding(.vertical, 10)
        }
    }

    private func etiquetaGrupo(_ texto: String) -> some View {
        Text(texto.uppercased())
            .font(.system(size: 10, weight: .medium))
            .tracking(0.8)
            .foregroundStyle(Theme.textFaint)
            .padding(.horizontal, 6)
            .padding(.top, 6)
            .padding(.bottom, 2)
    }

    private func fila(_ summary: ConversationSummary, fijado: Bool) -> some View {
        SidebarItem(
            title: summary.title,
            subtitle: summary.preview,
            meta: horaCorta(summary.updatedAt),
            selected: summary.id == chat.conversationID,
            onSelect: { abrir(summary) }
        ) {
            ItemAction(
                systemImage: fijado ? "pin.slash" : "pin",
                label: fijado ? "Desfijar chat" : "Fijar chat"
            ) {
                Task { adopt(await conversations.setPinned(summary.id, !fijado)) }
            }
            ItemAction(systemImage: "archivebox", label: "Archivar chat") {
                Task { adopt(await conversations.setArchived(summary.id, true)) }
            }
        }
        .contextMenu {
            Button {
                renombrando = summary
                nuevoNombre = summary.title
            } label: {
                Label("Renombrar chat", systemImage: "pencil")
            }
        }
    }

    /// Archivar es la ruta amable; el borrado destructivo vive SOLO aquí,
    /// dentro de Archivados, igual que en la web.
    private func filaArchivada(_ summary: ConversationSummary) -> some View {
        SidebarItem(
            title: summary.title,
            subtitle: summary.preview,
            meta: horaCorta(summary.archivedAt ?? summary.updatedAt),
            selected: summary.id == chat.conversationID,
            onSelect: { abrir(summary) }
        ) {
            ItemAction(systemImage: "arrow.uturn.backward", label: "Restaurar chat") {
                Task { adopt(await conversations.setArchived(summary.id, false)) }
            }
            ItemAction(systemImage: "xmark", label: "Borrar chat", destructiva: true) {
                borrando = summary
            }
        }
    }

    /// La hoja se cierra PRIMERO: si se espera a la red, el cambio ocurre
    /// oculto detrás y el usuario no ve nada.
    private func abrir(_ summary: ConversationSummary) {
        dismiss()
        Task { await chat.open(summary.id) }
    }

    private var buscando: Bool {
        !busqueda.trimmingCharacters(in: .whitespaces).isEmpty
    }

    /// La búsqueda le gana al colapso, igual que la web: un match archivado
    /// debe VERSE, no quedar tras el toggle.
    private var archivadosAbiertos: Bool { mostrarArchivados || buscando }

    private var fijados: [ConversationSummary] { conversations.pinned.filter(coincide) }
    private var activos: [ConversationSummary] { conversations.active.filter(coincide) }
    private var archivados: [ConversationSummary] { conversations.archived.filter(coincide) }

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
}
