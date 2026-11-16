import SwiftUI

/// El texto del asistente llega en markdown. Pintarlo crudo deja los asteriscos
/// y los backticks a la vista, que es la diferencia entre parecer un producto y
/// parecer un log. Los bloques cubren lo que la web renderiza vía
/// `markdownStyles`: encabezados, listas, citas, código en línea ámbar sobre
/// bloque oscuro, y ligas en esmeralda.
struct MarkdownText: View {
    let raw: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
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
            .font(.system(size: 16))
            .lineSpacing(5)
            .foregroundStyle(Theme.textAssistant)
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
        StreamedMarkdown.normalize(raw).components(separatedBy: "```").enumerated().flatMap { indice, parte -> [Bloque] in
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
