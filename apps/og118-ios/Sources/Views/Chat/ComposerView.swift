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

/// `ComposerFrame` compacto de la web: UNA fila (riel, texto, mic, enviar) y el
/// riel `footer-start` detrás del toggle de disclosure, que abre una fila debajo.
struct ComposerView: View {
    @FocusState private var tecladoActivo: Bool
    @State private var rielAbierto = false
    @Binding var draft: String
    let isStreaming: Bool
    let elementoActivo: Element?
    let tieneProyecto: Bool
    let aparicion: Animation?
    let adjuntos: [AdjuntosModel.Borrador]
    let lugaresLibres: Int
    let onArchivos: ([AdjuntosModel.Archivo]) -> Void
    let onQuitarAdjunto: (UUID) -> Void
    let onSend: (String) -> Void
    let onStop: () -> Void
    let grabando: Bool
    let transcribiendo: Bool
    let onDictar: () -> Void
    let onOpenContext: () -> Void
    @ObservedObject var llamada: ResonanceCallModel

    private var puedeEnviar: Bool {
        (!draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || !adjuntos.isEmpty) && !isStreaming
    }

    /// El teclado se baja al enviar: arriba tapa media conversación justo
    /// cuando llega la respuesta que el usuario quiere leer.
    private func enviar() {
        guard puedeEnviar else { return }
        tecladoActivo = false
        onSend(draft)
        draft = ""
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            if llamada.activa {
                ResonanceCallBar(estado: llamada.estado, bandas: llamada.bandas, etiqueta: llamada.etiqueta)
                    .transition(.opacity)
            }
            if !adjuntos.isEmpty {
                ChipsDeAdjuntos(borradores: adjuntos, deshabilitado: isStreaming, onQuitar: onQuitarAdjunto)
                    .transition(.opacity)
            }
            HStack(alignment: .bottom, spacing: 6) {
                toggleRiel
                TextField(
                    "",
                    text: $draft,
                    prompt: Text("Pregúntale a og118").foregroundStyle(Theme.textMuted),
                    axis: .vertical
                )
                .accessibilityIdentifier("composer")
                .focused($tecladoActivo)
                .submitLabel(.send)
                .onSubmit(enviar)
                .lineLimit(1...6)
                .textFieldStyle(.plain)
                .font(.system(size: 16))
                .foregroundStyle(Theme.text)
                .padding(.vertical, 10)
                .frame(minHeight: 44)
                botonDictar
                if isStreaming {
                    botonDetener
                } else {
                    botonEnviar
                }
            }
            if rielAbierto {
                riel.transition(.opacity.combined(with: .move(edge: .top)))
            } else if llamada.activa {
                botonLlamar.padding(.bottom, 2).transition(.opacity)
            }
        }
        .padding(4)
        .background(Theme.surface, in: RoundedRectangle(cornerRadius: Theme.radius))
        .background(.ultraThinMaterial.opacity(0.25), in: RoundedRectangle(cornerRadius: Theme.radius))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.radius).stroke(Theme.surfaceBorder, lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.5), radius: 25, x: 0, y: 12)
        .padding(.horizontal, 12)
        .padding(.bottom, 8)
        .padding(.top, 6)
        .animation(aparicion, value: rielAbierto)
        .animation(aparicion, value: adjuntos.count)
        .animation(aparicion, value: llamada.activa)
    }

    /// En llamada el botón sobrevive al riel cerrado (`keepWhenRailCollapses`
    /// en la web): colgar nunca queda escondido detrás de un toggle.
    private var botonLlamar: some View {
        ResonanceCallButton(activa: llamada.activa) { llamada.alternar() }
    }

    private var toggleRiel: some View {
        Button {
            rielAbierto.toggle()
        } label: {
            Image(systemName: "slider.horizontal.3")
                .font(.system(size: 17, weight: .medium))
                .foregroundStyle(rielAbierto ? Theme.textBody : Theme.textFaint)
                .frame(width: 44, height: 44)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(rielAbierto ? Color.white.opacity(0.06) : .clear)
                )
                .contentShape(Rectangle())
        }
        .accessibilityLabel("Más opciones")
        .accessibilityValue(rielAbierto ? "abierto" : "cerrado")
    }

    /// El selector de Elemento vive en el riel: afecta el próximo turno, así
    /// que va junto al input (COMPOSER-SWITCH-1).
    private var riel: some View {
        HStack(spacing: 8) {
            AdjuntarMenu(lugaresLibres: lugaresLibres, onArchivos: onArchivos)
            selectorDeElemento
            botonLlamar
        }
        .padding(.bottom, 2)
    }

    private var selectorDeElemento: some View {
        Button(action: onOpenContext) {
            HStack(spacing: 8) {
                AtomicBadge(elemento: elementoActivo, activo: elementoActivo != nil)
                Text(elementoActivo?.displayName ?? "og118 (base)")
                    .font(.system(size: 14))
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
            .frame(height: 38)
            .background(Theme.chipFill, in: RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.chipBorder, lineWidth: 1))
        }
        .frame(minHeight: 44)
        .accessibilityLabel("Seleccionar elemento")
        .contentTransition(.opacity)
        .animation(aparicion, value: elementoActivo?.token)
    }

    /// Un toque graba, otro transcribe y llena el composer; mientras
    /// transcribe queda ocupado para no encimar dos peticiones.
    private var botonDictar: some View {
        Button(action: onDictar) {
            Group {
                if transcribiendo {
                    ProgressView().scaleEffect(0.7).tint(Theme.textMuted)
                } else {
                    Image(systemName: grabando ? "stop.circle.fill" : "mic")
                        .font(.system(size: 18, weight: .regular))
                        .foregroundStyle(grabando ? Theme.stopFill : Theme.textMuted)
                }
            }
            .frame(width: 44, height: 44)
            .background {
                if grabando {
                    Circle().stroke(Theme.stopBorder, lineWidth: 1).padding(5)
                }
            }
            .contentShape(Rectangle())
        }
        .disabled(transcribiendo)
        .accessibilityLabel(grabando ? "Detener y transcribir" : "Iniciar dictado por voz")
    }

    /// `.og-send-btn`: deshabilitado es contorno (conserva la forma en el estado
    /// que más se ve); con texto, el gradiente esmeralda.
    private var botonEnviar: some View {
        Button {
            enviar()
        } label: {
            Image(systemName: "paperplane")
                .font(.system(size: 18, weight: .regular))
                .foregroundStyle(puedeEnviar ? Theme.sendText : Theme.textMuted)
                .frame(width: 44, height: 44)
                .background {
                    if puedeEnviar {
                        RoundedRectangle(cornerRadius: Theme.menuButtonRadius)
                            .fill(Theme.sendGradient)
                            .shadow(color: Theme.accentDeep.opacity(0.25), radius: 5, y: 2)
                    } else {
                        RoundedRectangle(cornerRadius: Theme.menuButtonRadius)
                            .stroke(Theme.sendDisabledBorder, lineWidth: 1)
                    }
                }
                .contentShape(Rectangle())
        }
        .disabled(!puedeEnviar)
        .accessibilityIdentifier("enviar")
        .accessibilityLabel("Enviar mensaje")
    }

    private var botonDetener: some View {
        Button(action: onStop) {
            Image(systemName: "stop.fill")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(Theme.stopText)
                .frame(width: 44, height: 44)
                .background(
                    RoundedRectangle(cornerRadius: Theme.menuButtonRadius).fill(Theme.stopFill)
                )
                .overlay(
                    RoundedRectangle(cornerRadius: Theme.menuButtonRadius).stroke(Theme.stopBorder, lineWidth: 1)
                )
                .contentShape(Rectangle())
        }
        .accessibilityLabel("Detener respuesta")
    }
}
