import SwiftUI

/// El badge «53 · I» del selector web (`atomicBadge` en Og118ElementSelector):
/// número atómico y símbolo en monoespaciada; «og» para el companion base.
struct AtomicBadge: View {
    let elemento: Element?
    let activo: Bool

    var body: some View {
        Text(elemento.map { "\($0.atomicNumber) · \($0.symbol)" } ?? "og")
            .font(.system(size: 11, weight: .semibold, design: .monospaced))
            .foregroundStyle(activo ? Theme.badgeSelectedText : Theme.textBody)
            .padding(.horizontal, 6)
            .padding(.vertical, 3)
            .background(activo ? Theme.badgeSelected : Color.white.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 4))
    }
}

/// La caja frosted de la web (`ComposerFrame` + `.glass-chat-composer`):
/// textarea arriba y el riel de controles abajo — chip de Elemento a la
/// izquierda, enviar/detener a la derecha. El chip vive aquí y no en el
/// header por paridad con COMPOSER-SWITCH-1: afecta el próximo turno, así
/// que va junto al input.
struct ComposerView: View {
    @Binding var draft: String
    let isStreaming: Bool
    let elementoActivo: Element?
    let tieneProyecto: Bool
    let aparicion: Animation?
    let onSend: (String) -> Void
    let onStop: () -> Void
    let onOpenContext: () -> Void

    private var puedeEnviar: Bool {
        !draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !isStreaming
    }

    var body: some View {
        VStack(spacing: 0) {
            TextField("Pregúntale a og118…", text: $draft, axis: .vertical)
                .lineLimit(1...6)
                .textFieldStyle(.plain)
                .font(.body)
                .foregroundStyle(Theme.text)
                .padding(.horizontal, 14)
                .padding(.top, 12)
                .padding(.bottom, 8)
            HStack(spacing: 8) {
                chipElemento
                Spacer(minLength: 8)
                if isStreaming {
                    botonDetener
                } else {
                    botonEnviar
                }
            }
            .padding(.leading, 10)
            .padding(.trailing, 6)
            .padding(.bottom, 5)
        }
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16).stroke(Theme.surfaceBorder, lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.5), radius: 25, x: 0, y: 12)
        .padding(.horizontal, 12)
        .padding(.bottom, 8)
        .padding(.top, 6)
    }

    /// El folder marca que hay proyecto activo alimentando el turno.
    private var chipElemento: some View {
        Button(action: onOpenContext) {
            HStack(spacing: 6) {
                if let elemento = elementoActivo {
                    AtomicBadge(elemento: elemento, activo: true)
                }
                Text(elementoActivo?.displayName ?? "og118 (base)")
                    .font(.subheadline)
                    .foregroundStyle(Theme.textBody)
                    .lineLimit(1)
                if tieneProyecto {
                    Image(systemName: "folder.fill")
                        .font(.system(size: 10))
                        .foregroundStyle(Theme.accent.opacity(0.8))
                }
                Image(systemName: "chevron.down")
                    .font(.system(size: 9, weight: .semibold))
                    .foregroundStyle(Theme.textMuted)
            }
            .padding(.horizontal, 10)
            .frame(minHeight: 34)
            .background(Theme.chipFill)
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .overlay(
                RoundedRectangle(cornerRadius: 10).stroke(Theme.chipBorder, lineWidth: 1)
            )
        }
        .frame(minHeight: 44)
        .frame(maxWidth: 200, alignment: .leading)
        .contentTransition(.opacity)
        .animation(aparicion, value: elementoActivo?.token)
        .animation(aparicion, value: tieneProyecto)
    }

    /// El `og-send-btn` de la web: cuadrado redondeado con el gradiente
    /// esmeralda; deshabilitado queda como contorno para no perder la forma.
    private var botonEnviar: some View {
        Button {
            onSend(draft)
            draft = ""
        } label: {
            Image(systemName: "arrow.up")
                .font(.system(size: 15, weight: .semibold))
                .foregroundStyle(puedeEnviar ? Theme.sendText : Theme.textMuted)
                .frame(width: 34, height: 34)
                .background {
                    if puedeEnviar {
                        RoundedRectangle(cornerRadius: 10)
                            .fill(Theme.sendGradient)
                            .shadow(color: Theme.accentDeep.opacity(0.25), radius: 5, y: 2)
                    } else {
                        RoundedRectangle(cornerRadius: 10)
                            .stroke(Theme.sendDisabledBorder, lineWidth: 1)
                    }
                }
                .frame(width: 44, height: 44)
                .contentShape(Rectangle())
        }
        .disabled(!puedeEnviar)
    }

    private var botonDetener: some View {
        Button(action: onStop) {
            Image(systemName: "stop.fill")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(Theme.stopText)
                .frame(width: 34, height: 34)
                .background(
                    RoundedRectangle(cornerRadius: 10).fill(Theme.stopFill)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 10).stroke(Theme.stopBorder, lineWidth: 1)
                )
                .frame(width: 44, height: 44)
                .contentShape(Rectangle())
        }
    }
}
