import SwiftUI

struct TypingIndicator: View {
    @State private var fase = 0.0

    var body: some View {
        HStack(spacing: 5) {
            ForEach(0..<3, id: \.self) { i in
                Circle()
                    .fill(Theme.typingDot)
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
