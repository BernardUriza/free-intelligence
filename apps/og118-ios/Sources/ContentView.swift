import SwiftUI

/// El orquestador: decide entre login y conversación, arma la pantalla del
/// chat (header + hilo/tarjeta + composer) y presenta las dos hojas. La
/// carne vive en SignInView, TranscriptView, StartCard, ComposerView,
/// ConversationsSheet y ContextSheet.
struct ContentView: View {
    @EnvironmentObject private var auth: Auth
    @StateObject private var chat: ChatModel
    @StateObject private var conversations: ConversationsModel
    @StateObject private var catalog: CatalogModel
    @StateObject private var voz: VoiceModel
    @ObservedObject var diagnostico: TurnDiagnostics
    @State private var draft = ""
    @State private var showingConversations = false
    @State private var showingContext = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// Mismo contrato que fi-glass: 0.3s ease-out, y NADA si el usuario pidió
    /// movimiento reducido (`prefers-reduced-motion`).
    private var aparicion: Animation? {
        reduceMotion ? nil : .easeOut(duration: 0.3)
    }

    init(chat: ChatModel, conversations: ConversationsModel, catalog: CatalogModel, voz: VoiceModel, diagnostico: TurnDiagnostics) {
        _chat = StateObject(wrappedValue: chat)
        _conversations = StateObject(wrappedValue: conversations)
        _catalog = StateObject(wrappedValue: catalog)
        _voz = StateObject(wrappedValue: voz)
        self.diagnostico = diagnostico
    }

    var body: some View {
        ZStack {
            GlassBackground()
            if auth.isSignedIn {
                conversation
                    .task {
                        await chat.restoreThread()
                        if SondaDeTurno.pedida() {
                            await SondaDeTurno.correr(chat)
                        }
                    }
                    .sheet(isPresented: $showingConversations) {
                        ConversationsSheet(chat: chat, conversations: conversations)
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
        VStack(spacing: 0) {
            encabezado
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
            composer
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
    }

    private var encabezado: some View {
        HStack(spacing: 4) {
            Button { showingConversations = true } label: {
                Image(systemName: "line.3.horizontal")
                    .font(.system(size: 17, weight: .medium))
                    .foregroundStyle(Theme.textMuted)
                    .frame(width: 44, height: 44)
            }
            Spacer(minLength: 0)
            Wordmark(size: 16)
            Spacer(minLength: 0)
            Button { chat.startNew() } label: {
                Image(systemName: "square.and.pencil")
                    .font(.system(size: 17, weight: .medium))
                    .foregroundStyle(Theme.textMuted)
                    .frame(width: 44, height: 44)
            }
        }
        .padding(.horizontal, 6)
        .overlay(alignment: .bottom) {
            Rectangle().fill(Theme.surfaceBorder).frame(height: 0.5)
        }
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
            onSend: { chat.send($0) },
            onStop: { chat.cancel() },
            grabando: voz.grabando,
            transcribiendo: voz.transcribiendo,
            onDictar: { voz.alternarDictado { texto in
                draft = draft.isEmpty ? texto : draft + " " + texto
            } },
            onOpenContext: { showingContext = true }
        )
    }
}
