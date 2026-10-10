import SwiftUI

/// El orquestador: login o conversación (hilo/tarjeta + composer bajo un botón
/// flotante, sin barra, como app.og118.ai), el drawer y la hoja de contexto.
struct ContentView: View {
    @EnvironmentObject private var auth: Auth
    @StateObject private var chat: ChatModel
    @StateObject private var conversations: ConversationsModel
    @StateObject private var catalog: CatalogModel
    @StateObject private var voz: VoiceModel
    @StateObject private var llamada: ResonanceCallModel
    @ObservedObject var diagnostico: TurnDiagnostics
    @State private var draft = ""
    @StateObject private var adjuntos = AdjuntosModel()
    @State private var drawerAbierto = false
    @GestureState private var arrastre: CGFloat = 0
    @State private var showingContext = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// Mismo contrato que fi-glass: 0.3s ease-out, y NADA si el usuario pidió
    /// movimiento reducido (`prefers-reduced-motion`).
    private var aparicion: Animation? {
        reduceMotion ? nil : .easeOut(duration: 0.3)
    }

    init(chat: ChatModel, conversations: ConversationsModel, catalog: CatalogModel, voz: VoiceModel, llamada: ResonanceCallModel, diagnostico: TurnDiagnostics) {
        _chat = StateObject(wrappedValue: chat)
        _conversations = StateObject(wrappedValue: conversations)
        _catalog = StateObject(wrappedValue: catalog)
        _voz = StateObject(wrappedValue: voz)
        _llamada = StateObject(wrappedValue: llamada)
        self.diagnostico = diagnostico
    }

    var body: some View {
        ZStack {
            GlassBackground()
            if auth.isSignedIn {
                conversation
                    .task {
                        await chat.restoreThread()
                        #if DEBUG
                        if SondaDeTurno.aperturaPedida() {
                            await SondaDeTurno.medirApertura(chat, conversations)
                            try? await Task.sleep(nanoseconds: 1_000_000_000)
                            CapturaDePantalla.emitir("chat-abierto")
                        } else if SondaDeTurno.fotoPedida() {
                            // Abre la hoja de chats y la fotografía: el e2e de
                            // la lista sin depender de que un humano mire.
                            drawerAbierto = true
                            try? await Task.sleep(nanoseconds: 1_500_000_000)
                            CapturaDePantalla.emitir("lista-cargando")
                            try? await Task.sleep(nanoseconds: 12_000_000_000)
                            CapturaDePantalla.emitir("lista-final")
                        } else if SondaDeTurno.pedida() {
                            await SondaDeTurno.revisarLista(conversations)
                            await SondaDeTurno.correr(chat)
                        }
                        #endif
                    }
                    .sheet(isPresented: $showingContext) {
                        ContextSheet(chat: chat, catalog: catalog)
                    }
                    .task { await catalog.refresh() }
            } else {
                SignInView()
            }
        }
        .preferredColorScheme(.dark)
        .tint(Theme.accent)
    }

    private var conversation: some View {
        ZStack(alignment: .topLeading) {
            Watermark()
            VStack(spacing: 0) {
                ZStack {
                    if chat.messages.isEmpty && !chat.isStreaming {
                        StartCard().transition(.opacity)
                    } else {
                        TranscriptView(chat: chat, voz: voz, diagnostico: diagnostico, aparicion: aparicion).transition(.opacity)
                    }
                }
                .id(chat.conversationID)
                .animation(aparicion, value: chat.conversationID)
                .animation(aparicion, value: chat.messages.isEmpty)
                if let error = voz.errorMessage {
                    aviso(error) { voz.errorMessage = nil }.transition(.opacity)
                }
                if let error = adjuntos.error {
                    aviso(error) { adjuntos.error = nil }.transition(.opacity)
                }
                composer
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
            MenuButton { abrirDrawer(true) }
                .padding(.leading, 10)
                .padding(.top, 4)
            bordeDeApertura
            drawer
        }
    }

    /// `useEdgeSwipe` de la web: arrastrar desde el borde izquierdo abre el
    /// drawer, y arrastrarlo hacia la izquierda lo cierra.
    private var bordeDeApertura: some View {
        Color.clear
            .frame(width: 16)
            .frame(maxHeight: .infinity)
            .contentShape(Rectangle())
            .gesture(
                DragGesture(minimumDistance: 12).onEnded { gesto in
                    if gesto.translation.width > 60 { abrirDrawer(true) }
                }
            )
            .allowsHitTesting(!drawerAbierto)
    }

    @ViewBuilder
    private var drawer: some View {
        if drawerAbierto {
            Color.black.opacity(0.5)
                .ignoresSafeArea()
                .onTapGesture { abrirDrawer(false) }
                .transition(.opacity)
                .accessibilityLabel("Cerrar conversaciones")
            ConversationsDrawer(chat: chat, conversations: conversations) { abrirDrawer(false) }
                .frame(width: Theme.drawerWidth)
                .frame(maxHeight: .infinity)
                .shadow(color: .black.opacity(0.55), radius: 40)
                .offset(x: min(0, arrastre))
                .gesture(
                    DragGesture(minimumDistance: 12)
                        .updating($arrastre) { gesto, estado, _ in estado = gesto.translation.width }
                        .onEnded { gesto in
                            if gesto.translation.width < -70 { abrirDrawer(false) }
                        }
                )
                .transition(.move(edge: .leading))
        }
    }

    /// `Og118VoiceErrorBanner`: voz y adjuntos avisan sobre el composer, visible
    /// aunque el hilo esté vacío — dentro del hilo, la tarjeta de inicio lo tapaba.
    private func aviso(_ texto: String, descartar: @escaping () -> Void) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Text(texto)
                .font(.footnote)
                .foregroundStyle(Theme.danger)
                .frame(maxWidth: .infinity, alignment: .leading)
            Button(action: descartar) {
                Image(systemName: "xmark")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(Theme.textMuted)
                    .frame(width: 44, height: 44)
            }
            .accessibilityLabel("Descartar aviso")
        }
        .padding(.leading, 14)
        .background(Theme.danger.opacity(0.08), in: RoundedRectangle(cornerRadius: 10))
        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Theme.danger.opacity(0.3), lineWidth: 1))
        .padding(.horizontal, 12)
    }

    private func abrirDrawer(_ abrir: Bool) {
        withAnimation(reduceMotion ? nil : .easeOut(duration: 0.25)) { drawerAbierto = abrir }
    }

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
            adjuntos: adjuntos.borradores,
            lugaresLibres: adjuntos.lugaresLibres,
            onArchivos: { archivos in Task { await adjuntos.agregar(archivos) } },
            onQuitarAdjunto: { adjuntos.quitar($0) },
            onSend: { texto in
                chat.send(texto, images: adjuntos.imagenes)
                adjuntos.vaciar()
            },
            onStop: { chat.cancel() },
            grabando: voz.grabando,
            transcribiendo: voz.transcribiendo,
            onDictar: { voz.alternarDictado { texto in
                draft = draft.isEmpty ? texto : draft + " " + texto
            } },
            onOpenContext: { showingContext = true },
            llamada: llamada
        )
    }
}
