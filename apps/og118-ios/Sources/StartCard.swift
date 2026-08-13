import SwiftUI

/// La tarjeta de arranque de la web (`Og118StartScreen`): casilla del
/// oganesón, wordmark, y el mismo copy sobre vidrio.
struct StartCard: View {
    var body: some View {
        VStack {
            Spacer()
            VStack(spacing: 14) {
                VStack(spacing: 2) {
                    Text("118")
                        .font(.system(size: 12, weight: .medium, design: .monospaced))
                        .foregroundStyle(Theme.textMuted)
                    Text("Og")
                        .font(.system(size: 34, weight: .bold))
                        .foregroundStyle(Theme.accent)
                    Text("Oganesson")
                        .font(.system(size: 10))
                        .foregroundStyle(Theme.textMuted)
                }
                .frame(width: 88, height: 88)
                .background(Color.white.opacity(0.04))
                .clipShape(RoundedRectangle(cornerRadius: 14))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(Theme.accent.opacity(0.35), lineWidth: 1)
                )
                .shadow(color: Theme.accent.opacity(0.15), radius: 16, y: 8)

                Wordmark(size: 30)

                Text("Og · 118 · Oganesson — synthetic, the heaviest known, the end of the table.")
                    .font(.footnote)
                    .foregroundStyle(Theme.textMuted)
                    .multilineTextAlignment(.center)

                Text("A personal thinking companion on the Free Intelligence substrate. Glass-box by design — you see the reasoning, not just the answer.")
                    .font(.subheadline)
                    .foregroundStyle(Theme.authorName)
                    .multilineTextAlignment(.center)
                    .lineSpacing(3)
            }
            .padding(.vertical, 34)
            .padding(.horizontal, 26)
            .frame(maxWidth: .infinity)
            .background(Theme.bgMid.opacity(0.55))
            .clipShape(RoundedRectangle(cornerRadius: 20))
            .overlay(
                RoundedRectangle(cornerRadius: 20)
                    .stroke(Color.white.opacity(0.18), lineWidth: 1)
            )
            .shadow(color: .black.opacity(0.45), radius: 30, y: 20)
            .padding(.horizontal, 20)
            Spacer()
        }
        .frame(maxWidth: .infinity)
    }
}
