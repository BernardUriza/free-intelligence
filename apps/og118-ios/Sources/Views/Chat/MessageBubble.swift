import SwiftUI

/// El texto del asistente llega en markdown. Pintarlo crudo deja los asteriscos
/// y los backticks a la vista, que es la diferencia entre parecer un producto y
/// parecer un log. Los bloques cubren lo que la web renderiza vía
/// `markdownStyles`: encabezados, listas, citas, código en línea ámbar sobre
/// bloque oscuro, y ligas en esmeralda.
struct MarkdownText: View {
    let raw: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(Array(bloques.enumerated()), id: \.offset) { _, bloque in
                render(bloque)
            }
        }
    }

    @ViewBuilder
    private func render(_ bloque: Bloque) -> some View {
        switch bloque {
        case .codigo(let codigo):
            ScrollView(.horizontal, showsIndicators: false) {
                Text(codigo)
                    .font(.system(.footnote, design: .monospaced))
                    .foregroundStyle(Theme.textBody)
                    .textSelection(.enabled)
                    .padding(10)
            }
            .background(Theme.codeBlockBg)
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .stroke(Theme.codeBlockBorder, lineWidth: 1)
            )
        case .encabezado(let nivel, let texto):
            Text(enLinea(texto))
                .font(.system(size: nivel == 1 ? 18 : (nivel == 2 ? 16 : 15), weight: .semibold))
                .foregroundStyle(Theme.text)
                .padding(.top, 4)
        case .vinetas(let items):
            VStack(alignment: .leading, spacing: 5) {
                ForEach(Array(items.enumerated()), id: \.offset) { _, item in
                    HStack(alignment: .top, spacing: 7) {
                        Text("•")
                            .font(.caption)
                            .foregroundStyle(Theme.textFaint)
                            .padding(.top, 3)
                        parrafo(item)
                    }
                }
            }
        case .numerada(let items):
            VStack(alignment: .leading, spacing: 5) {
                ForEach(Array(items.enumerated()), id: \.offset) { indice, item in
                    HStack(alignment: .top, spacing: 7) {
                        Text("\(indice + 1).")
                            .font(.callout)
                            .foregroundStyle(Theme.textFaint)
                        parrafo(item)
                    }
                }
            }
        case .cita(let texto):
            HStack(spacing: 0) {
                Rectangle().fill(Theme.quoteAccent).frame(width: 2)
                parrafo(texto)
                    .padding(.vertical, 8)
                    .padding(.horizontal, 12)
            }
            .background(Theme.quoteBg)
            .clipShape(RoundedRectangle(cornerRadius: 8))
        case .texto(let texto):
            parrafo(texto)
        }
    }

    private func parrafo(_ texto: String) -> some View {
        Text(enLinea(texto))
            .font(.body)
            .foregroundStyle(Theme.textBody)
            .textSelection(.enabled)
            .fixedSize(horizontal: false, vertical: true)
            .tint(Theme.accent)
    }

    private enum Bloque {
        case texto(String)
        case codigo(String)
        case encabezado(Int, String)
        case vinetas([String])
        case numerada([String])
        case cita(String)
    }

    private var bloques: [Bloque] {
        raw.components(separatedBy: "```").enumerated().flatMap { indice, parte -> [Bloque] in
            let limpio = parte.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !limpio.isEmpty else { return [] }
            guard indice.isMultiple(of: 2) else {
                let sinLenguaje = limpio.contains("\n")
                    ? String(limpio.drop(while: { $0 != "\n" })).trimmingCharacters(in: .newlines)
                    : limpio
                return [.codigo(sinLenguaje)]
            }
            return estructurar(limpio)
        }
    }

    /// Divide un tramo sin código en párrafos, encabezados, listas y citas,
    /// línea por línea, agrupando las líneas contiguas del mismo tipo.
    private func estructurar(_ tramo: String) -> [Bloque] {
        var resultado: [Bloque] = []
        var parrafoActual: [String] = []
        var vinetasActuales: [String] = []
        var numeradasActuales: [String] = []
        var citaActual: [String] = []

        func cerrarParrafo() {
            if !parrafoActual.isEmpty {
                resultado.append(.texto(parrafoActual.joined(separator: "\n")))
                parrafoActual = []
            }
        }
        func cerrarListas() {
            if !vinetasActuales.isEmpty {
                resultado.append(.vinetas(vinetasActuales))
                vinetasActuales = []
            }
            if !numeradasActuales.isEmpty {
                resultado.append(.numerada(numeradasActuales))
                numeradasActuales = []
            }
        }
        func cerrarCita() {
            if !citaActual.isEmpty {
                resultado.append(.cita(citaActual.joined(separator: "\n")))
                citaActual = []
            }
        }
        func cerrarTodo() {
            cerrarParrafo()
            cerrarListas()
            cerrarCita()
        }

        for lineaCruda in tramo.components(separatedBy: "\n") {
            let linea = lineaCruda.trimmingCharacters(in: .whitespaces)
            if linea.isEmpty {
                cerrarTodo()
            } else if let encabezado = comoEncabezado(linea) {
                cerrarTodo()
                resultado.append(.encabezado(encabezado.0, encabezado.1))
            } else if let item = comoVineta(linea) {
                cerrarParrafo()
                cerrarCita()
                if !numeradasActuales.isEmpty {
                    resultado.append(.numerada(numeradasActuales))
                    numeradasActuales = []
                }
                vinetasActuales.append(item)
            } else if let item = comoNumerada(linea) {
                cerrarParrafo()
                cerrarCita()
                if !vinetasActuales.isEmpty {
                    resultado.append(.vinetas(vinetasActuales))
                    vinetasActuales = []
                }
                numeradasActuales.append(item)
            } else if linea.hasPrefix("> ") || linea == ">" {
                cerrarParrafo()
                cerrarListas()
                citaActual.append(String(linea.dropFirst(linea == ">" ? 1 : 2)))
            } else {
                cerrarListas()
                cerrarCita()
                parrafoActual.append(linea)
            }
        }
        cerrarTodo()
        return resultado
    }

    private func comoEncabezado(_ linea: String) -> (Int, String)? {
        for nivel in (1...3).reversed() {
            let prefijo = String(repeating: "#", count: nivel) + " "
            if linea.hasPrefix(prefijo) {
                return (nivel, String(linea.dropFirst(prefijo.count)))
            }
        }
        return nil
    }

    private func comoVineta(_ linea: String) -> String? {
        for prefijo in ["- ", "* ", "• "] where linea.hasPrefix(prefijo) {
            return String(linea.dropFirst(prefijo.count))
        }
        return nil
    }

    private func comoNumerada(_ linea: String) -> String? {
        guard let punto = linea.firstIndex(of: "."),
              linea.index(after: punto) < linea.endIndex,
              linea[linea.index(after: punto)] == " ",
              !linea[linea.startIndex..<punto].isEmpty,
              linea[linea.startIndex..<punto].allSatisfy(\.isNumber)
        else { return nil }
        return String(linea[linea.index(punto, offsetBy: 2)...])
    }

    /// Markdown en línea (negritas, cursivas, `código`, ligas) con los colores
    /// de la web: código ámbar monoespaciado, ligas esmeralda subrayadas.
    private func enLinea(_ texto: String) -> AttributedString {
        guard var attr = try? AttributedString(
            markdown: texto,
            options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        ) else { return AttributedString(texto) }
        for run in attr.runs {
            if run.inlinePresentationIntent?.contains(.code) == true {
                attr[run.range].foregroundColor = Theme.codeInline
                attr[run.range].font = .system(.callout, design: .monospaced)
            }
            if run.link != nil {
                attr[run.range].foregroundColor = Theme.accent
                attr[run.range].underlineStyle = .single
            }
        }
        return attr
    }
}

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

struct MessageBubble: View {
    let role: ChatMessage.Role
    let text: String
    let author: String?
    var timestamp: String?
    var leyendo: Bool = false
    var sintetizando: Bool = false
    var onLeer: (() -> Void)?

    private var esUsuario: Bool { role == .user }

    /// Geometría de `glass-chat-bubble-*`: 16 pt de radio con la esquina
    /// inferior del lado del hablante cortada a 4.
    private var forma: UnevenRoundedRectangle {
        UnevenRoundedRectangle(
            topLeadingRadius: 16,
            bottomLeadingRadius: esUsuario ? 16 : 4,
            bottomTrailingRadius: esUsuario ? 4 : 16,
            topTrailingRadius: 16
        )
    }

    /// Escuchar la respuesta. Segundo toque detiene; mientras sintetiza el
    /// servidor, el control queda ocupado en vez de aceptar otra petición.
    private func botonLeer(_ accion: @escaping () -> Void) -> some View {
        Button(action: accion) {
            HStack(spacing: 5) {
                if sintetizando {
                    ProgressView().scaleEffect(0.6).tint(Theme.textFaint)
                } else {
                    Image(systemName: leyendo ? "stop.fill" : "speaker.wave.2")
                        .font(.system(size: 11, weight: .semibold))
                }
                Text(leyendo ? "Detener" : "Escuchar").font(.caption2)
            }
            .foregroundStyle(leyendo ? Theme.accent : Theme.textFaint)
            .frame(minHeight: 28)
        }
        .disabled(sintetizando)
        .padding(.top, 2)
    }

    var body: some View {
        HStack(spacing: 0) {
            if esUsuario { Spacer(minLength: 48) }
            VStack(alignment: .leading, spacing: 7) {
                AuthorHeader(
                    esUsuario: esUsuario,
                    nombre: esUsuario ? "Tú" : (author ?? "og118"),
                    timestamp: timestamp
                )
                if esUsuario {
                    Text(text)
                        .font(.body)
                        .foregroundStyle(Theme.text)
                        .textSelection(.enabled)
                        .fixedSize(horizontal: false, vertical: true)
                } else {
                    MarkdownText(raw: text)
                    if let onLeer {
                        botonLeer(onLeer)
                    }
                }
            }
            .padding(.vertical, 11)
            .padding(.horizontal, 14)
            .background(esUsuario ? Theme.bubbleUser : Theme.bubbleAssistant)
            .clipShape(forma)
            .overlay(
                forma.stroke(
                    esUsuario ? Theme.bubbleUserBorder : Theme.bubbleBorder,
                    lineWidth: 1
                )
            )
            .contextMenu {
                Button {
                    UIPasteboard.general.string = text
                } label: {
                    Label("Copiar", systemImage: "doc.on.doc")
                }
                if let onLeer {
                    Button(action: onLeer) {
                        Label(leyendo ? "Detener" : "Escuchar", systemImage: leyendo ? "stop.fill" : "speaker.wave.2")
                    }
                }
            }
            if !esUsuario { Spacer(minLength: 24) }
        }
        .frame(maxWidth: .infinity, alignment: esUsuario ? .trailing : .leading)
    }
}

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
