import SwiftUI

/// La fila del sidebar, portada de fi-glass (`sidebarItemStyle.ts`) con sus
/// medidas exactas: gap 0.4rem, padding 0.55/0.6rem, radio 10, borde de 1px
/// transparente que sólo aparece al seleccionar, y la escala tipográfica
/// 0.85 / 0.75 / 0.68rem para título, subtítulo y meta.
///
/// En `pointer: coarse` la web muestra SIEMPRE las acciones (opacity 1) en vez
/// de revelarlas al hover — un teléfono no tiene hover, así que aquí van fijas.
private enum Medida {
    static let gap: CGFloat = 6
    static let padV: CGFloat = 9
    static let padH: CGFloat = 10
    static let radio: CGFloat = 10
    static let titulo: CGFloat = 14
    static let subtitulo: CGFloat = 12
    static let meta: CGFloat = 11
}

struct SidebarItem<Acciones: View>: View {
    let title: String
    let subtitle: String?
    let meta: String
    var selected = false
    let onSelect: () -> Void
    @ViewBuilder let acciones: () -> Acciones

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            // `.disabled(selected)` atenuaba TODO el contenido y la fila
            // abierta se veía apagada; en la web el seleccionado conserva su
            // contraste y sólo deja de ser clicable.
            Button(action: { if !selected { onSelect() } }) {
                // El cuerpo es una COLUMNA: título, subtítulo y la hora como
                // tercera línea. La hora al lado del título le robaba la mitad
                // del ancho y lo truncaba a media palabra.
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: Medida.titulo))
                        .foregroundStyle(Theme.text)
                        .lineLimit(1)
                        .truncationMode(.tail)
                    if let subtitle, !subtitle.isEmpty {
                        Text(subtitle)
                            .font(.system(size: Medida.subtitulo))
                            .foregroundStyle(Theme.textMuted)
                            .lineLimit(1)
                            .truncationMode(.tail)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            // En táctil no hay hover que revele las acciones, así que van
            // siempre visibles — pero en línea le robaban el ancho al título,
            // así que bajan a su propio renglón pegado a la derecha, con sus
            // blancos de 44pt intactos.
            // La hora comparte renglón con las acciones. El canónico las manda
            // a una línea propia para que el título no se trunque (su comentario
            // lo dice: "full-width readable title, intact 44px targets"); ese
            // renglón quedaba casi vacío y con 28 chats sólo cabían 6 en
            // pantalla. Fusionarlo con la hora conserva las dos garantías y
            // devuelve ~40pt por fila.
            HStack(spacing: 0) {
                Text(meta)
                    .font(.system(size: Medida.meta))
                    .foregroundStyle(Theme.itemMeta)
                    .monospacedDigit()
                Spacer(minLength: 8)
                acciones()
            }
        }
        .padding(.vertical, Medida.padV)
        .padding(.horizontal, Medida.padH)
        .background(
            RoundedRectangle(cornerRadius: Medida.radio)
                .fill(selected ? Theme.itemSelectedBg : .clear)
        )
        .overlay(
            RoundedRectangle(cornerRadius: Medida.radio)
                .stroke(selected ? Theme.itemSelectedBorder : .clear, lineWidth: 1)
        )
    }
}

/// El botón de acción de la fila (`fi-item-action`): 44×44 de área táctil con
/// el icono pequeño dentro, para no robarle ancho al título.
struct ItemAction: View {
    let systemImage: String
    let label: String
    var destructiva = false
    let accion: () -> Void

    var body: some View {
        Button(action: accion) {
            Image(systemName: systemImage)
                .font(.system(size: 13))
                .foregroundStyle(destructiva ? Theme.danger : Theme.itemAction)
                .frame(width: 44, height: 44)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }
}
