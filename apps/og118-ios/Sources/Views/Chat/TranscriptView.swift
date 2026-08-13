import SwiftUI

/// El hilo: burbujas dobladas, el turno vivo en streaming (typing indicator
/// hasta el primer token), el error del turno, y auto-scroll al fondo con el
/// botón de volver al final — el `fi-scroll-to-bottom` de la web.
struct TranscriptView: View {
    @ObservedObject var chat: ChatModel
    @ObservedObject var voz: VoiceModel
    let aparicion: Animation?

    @State private var alFondo = true

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 14) {
                    ForEach(chat.messages) { message in
                        MessageBubble(
                            role: message.role,
                            text: message.content,
                            author: message.author,
                            timestamp: message.timestamp,
                            leyendo: voz.reproductor.hablando == message.id.uuidString,
                            sintetizando: voz.sintetizando == message.id.uuidString,
                            onLeer: message.role == .assistant
                                ? { voz.alternarLectura(de: message.content, id: message.id.uuidString) }
                                : nil
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
                    if let error = voz.errorMessage {
                        Text(error)
                            .font(.footnote)
                            .foregroundStyle(Theme.danger)
                            .padding(.horizontal, 14)
                    }
                    if let error = chat.errorMessage {
                        Text(error)
                            .font(.footnote)
                            .foregroundStyle(Theme.danger)
                            .padding(.horizontal, 14)
                    }
                    centinelaDeFondo
                }
                .padding(.horizontal, 12)
                .padding(.top, 14)
                .animation(aparicion, value: chat.messages.count)
                .animation(aparicion, value: chat.isStreaming)
            }
            // API canónica de iOS 18: entrega la geometría real del scroll de
            // forma continua. Reemplaza el truco de GeometryReader+PreferenceKey,
            // que no dispara en el primer layout y no ve los content insets.
            .onScrollGeometryChange(for: Bool.self) { geo in
                let fin = geo.contentOffset.y + geo.containerSize.height
                let total = geo.contentSize.height + geo.contentInsets.bottom
                return fin >= total - 40
            } action: { _, estaAlFondo in
                if estaAlFondo != alFondo { alFondo = estaAlFondo }
            }
            .scrollDismissesKeyboard(.interactively)
            .overlay(alignment: .bottom) {
                if !alFondo {
                    botonAlFondo { irAlFondo(proxy, animado: true) }
                        .padding(.bottom, 10)
                        .transition(.opacity.combined(with: .scale(scale: 0.9)))
                }
            }
            .animation(aparicion, value: alFondo)
            .onChange(of: chat.messages.count) { _, _ in
                irAlFondo(proxy, animado: true)
            }
            .onChange(of: chat.liveText) { _, _ in
                // Sólo persigue el stream si el usuario NO se fue a leer arriba:
                // arrastrarlo de vuelta mientras lee es peor que no seguirlo.
                if alFondo { irAlFondo(proxy, animado: false) }
            }
        }
    }

    /// Centinela invisible: mientras su posición esté dentro del viewport, la
    /// vista está al fondo. Es la misma señal que usa el botón de la web, medida
    /// con geometría en vez de con el offset del scroll.
    private var centinelaDeFondo: some View {
        Color.clear.frame(height: 1).id("fondo")
    }

    private func irAlFondo(_ proxy: ScrollViewProxy, animado: Bool) {
        if animado {
            withAnimation(aparicion) { proxy.scrollTo("fondo", anchor: .bottom) }
        } else {
            proxy.scrollTo("fondo", anchor: .bottom)
        }
    }

    private func botonAlFondo(_ accion: @escaping () -> Void) -> some View {
        Button(action: accion) {
            Image(systemName: "arrow.down")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(Theme.text)
                .frame(width: 36, height: 36)
                .background(Theme.surface, in: Circle())
                .overlay(Circle().stroke(Theme.surfaceBorder, lineWidth: 1))
                .shadow(color: .black.opacity(0.4), radius: 10, y: 4)
        }
        .frame(width: 44, height: 44)
        .accessibilityLabel("Ir al final de la conversación")
    }
}


