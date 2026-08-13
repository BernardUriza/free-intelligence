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

/// El sidebar de la web como hoja: buscar, fijar, archivar, renombrar y
/// borrar, con los mismos gestos y la misma jerarquía que la web.
struct ConversationsSheet: View {
    @ObservedObject var chat: ChatModel
    @ObservedObject var conversations: ConversationsModel
    @Environment(\.dismiss) private var dismiss

    @State private var busqueda = ""
    @State private var mostrarArchivados = false
    @State private var renombrando: ConversationSummary?
    @State private var nuevoNombre = ""
    @State private var borrando: ConversationSummary?

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Button {
                        chat.startNew()
                        dismiss()
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
            dismiss()
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
            .tint(Theme.archiveSwipe)
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
            dismiss()
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
}
