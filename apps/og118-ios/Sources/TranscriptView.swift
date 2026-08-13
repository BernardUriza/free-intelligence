import SwiftUI

/// El hilo: burbujas dobladas, el turno vivo en streaming (typing indicator
/// hasta el primer token), el error del turno, y auto-scroll al fondo.
struct TranscriptView: View {
    @ObservedObject var chat: ChatModel
    let aparicion: Animation?

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 14) {
                    ForEach(chat.messages) { message in
                        MessageBubble(
                            role: message.role,
                            text: message.content,
                            author: message.author,
                            timestamp: message.timestamp
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
                    if let error = chat.errorMessage {
                        Text(error)
                            .font(.footnote)
                            .foregroundStyle(Theme.danger)
                            .padding(.horizontal, 14)
                    }
                    Color.clear.frame(height: 1).id("fondo")
                }
                .padding(.horizontal, 12)
                .padding(.top, 14)
                .animation(aparicion, value: chat.messages.count)
                .animation(aparicion, value: chat.isStreaming)
            }
            .onChange(of: chat.messages.count) { _, _ in
                withAnimation { proxy.scrollTo("fondo", anchor: .bottom) }
            }
            .onChange(of: chat.liveText) { _, _ in
                proxy.scrollTo("fondo", anchor: .bottom)
            }
        }
    }
}
