import SwiftUI

/// La fila «quién dijo esto» de fi-glass (`MessageAuthorHeader`): ficha de
/// avatar de 22 pt, nombre y hora. El usuario es violeta con «Tú»; el agente,
/// esmeralda con su símbolo (las dos primeras letras del nombre).
struct AuthorHeader: View {
    let esUsuario: Bool
    let nombre: String
    let timestamp: String?

    private var ficha: String {
        esUsuario ? "Tú" : String(nombre.prefix(2))
    }

    private var hora: String? {
        guard let timestamp, let fecha = ConversationSchema.fecha(timestamp) else { return nil }
        return fecha.formatted(date: .omitted, time: .shortened)
    }

    var body: some View {
        HStack(spacing: 6) {
            Text(ficha)
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(esUsuario ? Theme.text : Theme.authorAgentText)
                .frame(width: 22, height: 22)
                .background(esUsuario ? Theme.authorUser : Theme.accent)
                .clipShape(RoundedRectangle(cornerRadius: 6))
            Text(nombre)
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(Theme.authorName)
            if let hora {
                Text(hora)
                    .font(.system(size: 11))
                    .foregroundStyle(Theme.textFaint)
                    .monospacedDigit()
            }
        }
    }
}

/// La píldora `MessageModelBadge` de fi-glass: «Powered by» y el modelo que de
/// verdad contestó, en el acento.
struct ModelBadge: View {
    let model: String

    var body: some View {
        (Text("Powered by ").foregroundStyle(Theme.textMuted)
            + Text(model).foregroundStyle(Theme.accent))
            .font(.system(size: 11))
            .lineLimit(1)
            .padding(.vertical, 2)
            .padding(.horizontal, 8)
            .background(Theme.modelBadgeFill, in: Capsule())
            .overlay(Capsule().stroke(Theme.modelBadgeBorder, lineWidth: 1))
            .accessibilityLabel("Generado por \(model)")
    }
}

/// Burbuja de ancho completo y radio uniforme, como la web en móvil: og118 es
/// una IA, no un mensajero — el rol se lee por el tinte, no por el lado.
struct MessageBubble: View {
    let role: ChatMessage.Role
    let text: String
    let author: String?
    var timestamp: String?
    var model: String?
    var imagenes: [MessageImage] = []
    var reacciones: [String] = []
    var mostrarAcciones = false
    var leyendo = false
    var sintetizando = false
    var onLeer: (() -> Void)?
    var onTocar: (() -> Void)?

    @State private var copiado = false

    private var esUsuario: Bool { role == .user }

    private var forma: RoundedRectangle {
        RoundedRectangle(cornerRadius: Theme.bubbleRadiusCompact)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            AuthorHeader(
                esUsuario: esUsuario,
                nombre: esUsuario ? "Tú" : (author ?? "og118"),
                timestamp: timestamp
            )
            if !imagenes.isEmpty {
                ImagenesDelMensaje(imagenes: imagenes)
                    .padding(.vertical, 4)
            }
            if esUsuario {
                if !text.isEmpty {
                Text(text)
                    .font(.system(size: 16))
                    .lineSpacing(5)
                    .foregroundStyle(Theme.textBody)
                    .textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true)
                }
            } else {
                MarkdownText(raw: text)
                    .accessibilityIdentifier("respuesta")
                if !reacciones.isEmpty {
                    ReaccionesDelMensaje(reacciones: reacciones)
                }
                pie
            }
        }
        .padding(.vertical, Theme.bubblePadV)
        .padding(.horizontal, Theme.bubblePadH)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(esUsuario ? Theme.bubbleUser : Theme.bubbleAssistant, in: forma)
        .overlay(forma.stroke(esUsuario ? Theme.bubbleUserBorder : Theme.bubbleBorder, lineWidth: 1))
        .shadow(color: .black.opacity(0.12), radius: 6, y: 4)
        .contentShape(forma)
        .onTapGesture { onTocar?() }
        .contextMenu {
            Button(action: copiar) {
                Label("Copiar", systemImage: "doc.on.doc")
            }
            if let onLeer {
                Button(action: onLeer) {
                    Label(leyendo ? "Detener" : "Escuchar", systemImage: leyendo ? "stop.fill" : "speaker.wave.2")
                }
            }
        }
    }

    /// `fi-msg-footer`: la píldora del modelo siempre; copiar y escuchar sólo en
    /// el último mensaje o en el que se tocó, como `messageActionsStyle` en touch.
    @ViewBuilder
    private var pie: some View {
        if model != nil || mostrarAcciones {
            HStack(spacing: 8) {
                if let model { ModelBadge(model: model) }
                if mostrarAcciones {
                    accion(copiado ? "checkmark" : "doc.on.doc", etiqueta: "Copiar mensaje", accion: copiar)
                    if let onLeer {
                        Button(action: onLeer) {
                            Group {
                                if sintetizando {
                                    ProgressView().scaleEffect(0.6).tint(Theme.textFaint)
                                } else {
                                    Image(systemName: leyendo ? "stop.fill" : "speaker.wave.2")
                                        .font(.system(size: 14))
                                }
                            }
                            .foregroundStyle(leyendo ? Theme.accent : Theme.textMuted)
                            .frame(width: 44, height: 44)
                            .contentShape(Rectangle())
                        }
                        .disabled(sintetizando)
                        .accessibilityLabel(leyendo ? "Detener lectura" : "Escuchar mensaje")
                    }
                }
            }
            .frame(minHeight: 26)
            .padding(.top, 6)
            .transition(.opacity)
        }
    }

    private func accion(_ icono: String, etiqueta: String, accion: @escaping () -> Void) -> some View {
        Button(action: accion) {
            Image(systemName: icono)
                .font(.system(size: 14))
                .foregroundStyle(copiado ? Theme.accent : Theme.textMuted)
                .frame(width: 44, height: 44)
                .contentShape(Rectangle())
        }
        .accessibilityLabel(etiqueta)
    }

    private func copiar() {
        UIPasteboard.general.string = text
        copiado = true
        Task {
            try? await Task.sleep(nanoseconds: 1_500_000_000)
            copiado = false
        }
    }
}

/// Las reacciones como chips bajo el cuerpo, igual que `MessageReactions` en
/// fi-glass: un gesto sobre el mensaje, nunca texto dentro de él.
private struct ReaccionesDelMensaje: View {
    let reacciones: [String]

    var body: some View {
        HStack(spacing: 6) {
            ForEach(Array(reacciones.enumerated()), id: \.offset) { _, reaccion in
                Text(reaccion)
                    .font(.system(size: 14))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Theme.bubbleBorder, in: Capsule())
            }
        }
        .padding(.top, 2)
        .accessibilityIdentifier("reacciones")
    }
}
