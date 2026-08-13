import SwiftUI

/// El selector de contexto del turno (elemento + proyecto), espejo del
/// `Og118ElementSelector` de la web como hoja nativa.
struct ContextSheet: View {
    @ObservedObject var chat: ChatModel
    @ObservedObject var catalog: CatalogModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
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
            .background(Theme.engineChipFill)
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
            dismiss()
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
            dismiss()
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
}
