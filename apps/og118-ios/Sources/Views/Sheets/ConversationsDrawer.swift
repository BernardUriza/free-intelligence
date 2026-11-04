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

/// El sidebar de og118.ai como drawer lateral, con SU anatomía: wordmark y
/// «+ Nuevo chat» arriba, la lista, «Archivados (N)» fijo abajo y «Salir · correo».
struct ConversationsDrawer: View {
    @ObservedObject var chat: ChatModel
    @ObservedObject var conversations: ConversationsModel
    @EnvironmentObject private var auth: Auth
    let onClose: () -> Void

    @State private var busqueda = ""
    @State private var mostrarArchivados = false
    @State private var renombrando: ConversationSummary?
    @State private var nuevoNombre = ""
    @State private var borrando: ConversationSummary?
    @State private var esperaLarga = false

    var body: some View {
        contenido
            .background(Theme.bgDeep.ignoresSafeArea())
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

    private var encabezado: some View {
        HStack(alignment: .center, spacing: 8) {
            VStack(alignment: .leading, spacing: 2) {
                Wordmark(size: 17)
                Text(version)
                    .font(.system(size: 11))
                    .foregroundStyle(Theme.textFaint)
                    .lineLimit(1)
            }
            Spacer(minLength: 4)
            Button {
                chat.startNew()
                onClose()
            } label: {
                Text("+ Nuevo chat")
                    .font(.system(size: 15))
                    .foregroundStyle(Theme.accent)
                    .padding(.horizontal, 10)
                    .frame(height: 44)
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.accent, lineWidth: 1))
            }
            .accessibilityIdentifier("nuevo-chat")
        }
        .padding(.horizontal, 14)
        .padding(.top, 8)
        .padding(.bottom, 10)
        .overlay(alignment: .bottom) {
            Rectangle().fill(Theme.sidebarDivider).frame(height: 1)
        }
    }

    private var version: String {
        let info = Bundle.main.infoDictionary
        let corta = info?["CFBundleShortVersionString"] as? String ?? "?"
        let build = info?["CFBundleVersion"] as? String ?? "?"
        return "v\(corta) · build \(build)"
    }

    private var contenido: some View {
        VStack(spacing: 0) {
            encabezado
            buscador
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 5) {
                    if conversations.summaries.isEmpty {
                        estadoVacio
                    }
                    if archivadosAbiertos {
                        ForEach(archivados) { filaArchivada($0) }
                    }
                    if !archivadosAbiertos || buscando {
                        if !fijados.isEmpty {
                            etiquetaGrupo("Fijados")
                            ForEach(fijados) { fila($0, fijado: true) }
                        }
                        if !activos.isEmpty {
                            if !fijados.isEmpty { etiquetaGrupo("Chats") }
                            ForEach(activos) { fila($0, fijado: false) }
                        }
                    }
                    if buscando, fijados.isEmpty, activos.isEmpty, archivados.isEmpty {
                        Text("Sin resultados para «\(busqueda.trimmingCharacters(in: .whitespaces))».")
                            .font(.system(size: 12.5))
                            .foregroundStyle(Theme.textFaint)
                            .padding(8)
                    }
                }
                .padding(8)
                // El último chat quedaba mordido por el pie: sin este colchón
                // el scroll termina justo donde empieza la línea de abajo.
                .padding(.bottom, 12)
            }
            if !conversations.archived.isEmpty { filaArchivados }
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
            TextField("Buscar chats…", text: $busqueda)
                .font(.system(size: 15))
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

    /// `og-sidebar-archive-toggle`: fila fija sobre el pie; abierta, la lista
    /// muestra los archivados (donde vive el borrado) en lugar de los activos.
    private var filaArchivados: some View {
        Button {
            mostrarArchivados.toggle()
        } label: {
            HStack {
                Text("Archivados (\(conversations.archived.count))")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(Theme.text)
                Spacer()
                Image(systemName: mostrarArchivados ? "chevron.down" : "chevron.right")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(Theme.textMuted)
            }
            .padding(.horizontal, 14)
            .frame(minHeight: 72)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .overlay(alignment: .top) {
            Rectangle().fill(Theme.sidebarDivider).frame(height: 1)
        }
        .accessibilityLabel("Mostrar archivados")
    }

    private var pie: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Sincronizado en tu cuenta — disponible en todos tus dispositivos.")
                .font(.system(size: 12))
                .foregroundStyle(Theme.itemMeta)
                .fixedSize(horizontal: false, vertical: true)
            Button {
                onClose()
                auth.signOut()
            } label: {
                Text(auth.email.map { "Salir · \($0)" } ?? "Salir")
                    .font(.system(size: 13))
                    .foregroundStyle(Theme.textBody)
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .frame(maxWidth: .infinity)
                    .frame(height: 30)
                    .overlay(Capsule().stroke(Theme.surfaceBorder, lineWidth: 1))
            }
            .frame(minHeight: 44)
            .accessibilityLabel("Cerrar sesión")
        }
        .padding(.horizontal, 14)
        .padding(.top, 10)
        .padding(.bottom, 4)
        .overlay(alignment: .top) {
            Rectangle().fill(Theme.sidebarDivider).frame(height: 1)
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

    /// El preview del servidor es el último mensaje, que en un chat de un solo
    /// turno ES el título: la fila salía diciendo lo mismo dos veces.
    private func subtitulo(_ summary: ConversationSummary) -> String? {
        guard let preview = summary.preview?.trimmingCharacters(in: .whitespacesAndNewlines),
              !preview.isEmpty,
              preview.caseInsensitiveCompare(summary.title) != .orderedSame,
              !summary.title.hasPrefix(preview.prefix(40)) else { return nil }
        return preview
    }

    private func fila(_ summary: ConversationSummary, fijado: Bool) -> some View {
        SidebarItem(
            title: summary.title,
            subtitle: subtitulo(summary),
            meta: horaCorta(summary.updatedAt),
            selected: summary.id == chat.conversationID,
            onSelect: { abrir(summary) }
        ) {
            ItemAction(systemImage: "pencil", label: "Renombrar chat") {
                renombrando = summary
                nuevoNombre = summary.title
            }
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
    }

    /// Archivar es la ruta amable; el borrado destructivo vive SOLO aquí,
    /// dentro de Archivados, igual que en la web.
    private func filaArchivada(_ summary: ConversationSummary) -> some View {
        SidebarItem(
            title: summary.title,
            subtitle: subtitulo(summary),
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

    /// El drawer se cierra PRIMERO: si se espera a la red, el cambio ocurre
    /// oculto detrás y el usuario no ve nada.
    private func abrir(_ summary: ConversationSummary) {
        onClose()
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
