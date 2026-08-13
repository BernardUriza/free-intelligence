import SwiftUI

/// El texto del asistente llega en markdown. Pintarlo crudo deja los asteriscos
/// y los backticks a la vista, que es la diferencia entre parecer un producto y
/// parecer un log.
struct MarkdownText: View {
    let raw: String

    var body: some View {
        ForEach(Array(bloques.enumerated()), id: \.offset) { _, bloque in
            switch bloque {
            case .codigo(let codigo):
                ScrollView(.horizontal, showsIndicators: false) {
                    Text(codigo)
                        .font(.system(.footnote, design: .monospaced))
                        .foregroundStyle(Theme.accent)
                        .textSelection(.enabled)
                        .padding(10)
                }
                .background(Color.black.opacity(0.35))
                .clipShape(RoundedRectangle(cornerRadius: 10))
            case .texto(let texto):
                Text(atribuido(texto))
                    .font(.body)
                    .foregroundStyle(Theme.text)
                    .textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private enum Bloque {
        case texto(String)
        case codigo(String)
    }

    private var bloques: [Bloque] {
        raw.components(separatedBy: "```").enumerated().compactMap { indice, parte in
            let limpio = parte.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !limpio.isEmpty else { return nil }
            if indice.isMultiple(of: 2) { return .texto(limpio) }
            let sinLenguaje = limpio.contains("\n")
                ? String(limpio.drop(while: { $0 != "\n" })).trimmingCharacters(in: .newlines)
                : limpio
            return .codigo(sinLenguaje)
        }
    }

    private func atribuido(_ texto: String) -> AttributedString {
        (try? AttributedString(
            markdown: texto,
            options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        )) ?? AttributedString(texto)
    }
}

struct MessageBubble: View {
    let role: ChatMessage.Role
    let text: String
    let author: String?

    private var esUsuario: Bool { role == .user }

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            if !esUsuario {
                Text(author ?? "og118")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(Theme.accent)
            }
            if esUsuario {
                Text(text)
                    .font(.body)
                    .foregroundStyle(Theme.text)
                    .textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true)
            } else {
                MarkdownText(raw: text)
            }
        }
        .padding(.vertical, 11)
        .padding(.horizontal, 14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(esUsuario ? Theme.bubbleUser : Theme.bubbleAssistant)
        .clipShape(
            .rect(
                topLeadingRadius: 16,
                bottomLeadingRadius: esUsuario ? 16 : 5,
                bottomTrailingRadius: esUsuario ? 5 : 16,
                topTrailingRadius: 16
            )
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(esUsuario ? Theme.bubbleUserBorder : Theme.bubbleBorder, lineWidth: 1)
        )
        .padding(.leading, esUsuario ? 44 : 0)
        .padding(.trailing, esUsuario ? 0 : 44)
    }
}

struct TypingIndicator: View {
    @State private var fase = 0.0

    var body: some View {
        HStack(spacing: 5) {
            ForEach(0..<3, id: \.self) { i in
                Circle()
                    .fill(Theme.accent)
                    .frame(width: 7, height: 7)
                    .opacity(0.35 + 0.65 * abs(sin(fase + Double(i) * 0.7)))
            }
        }
        .onAppear {
            withAnimation(.linear(duration: 1.1).repeatForever(autoreverses: false)) {
                fase = .pi * 2
            }
        }
    }
}
