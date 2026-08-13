import Foundation

/// Puerto de `normalizeStreamedMarkdown` de fi-glass (B3-FIGLASS-9).
///
/// El backend concatena el texto previo a una herramienta con la respuesta sin
/// salto de línea, y sale `…necesarias.## Respuesta sobre…`: el `##` no empieza
/// renglón, así que CommonMark lo trata —correctamente— como texto de párrafo y
/// los gatos quedan a la vista.
///
/// Es un NORMALIZADOR, no un parser: una sola reparación conservadora, aplicada
/// únicamente fuera de los bloques de código. Exigir la puntuación pegada es lo
/// que evita los falsos positivos: `C# is nice`, `issue #123` y `use the # key`
/// quedan intactos.
enum StreamedMarkdown {
    private static let encabezadoPegado = try! NSRegularExpression(
        pattern: "([.!?:;,)\\]\"'»…])(#{1,6} )"
    )

    static func normalize(_ contenido: String) -> String {
        // Los fences quedan en los segmentos impares y no se tocan. Un fence sin
        // cerrar —que es lo normal a media transmisión— corre hasta el final.
        var resultado = ""
        var dentroDeCodigo = false
        for (indice, segmento) in contenido.components(separatedBy: "```").enumerated() {
            if indice > 0 { resultado += "```" }
            dentroDeCodigo = !indice.isMultiple(of: 2)
            resultado += dentroDeCodigo ? segmento : reparar(segmento)
        }
        return resultado
    }

    private static func reparar(_ tramo: String) -> String {
        let rango = NSRange(tramo.startIndex..., in: tramo)
        return encabezadoPegado.stringByReplacingMatches(
            in: tramo,
            range: rango,
            withTemplate: "$1\n\n$2"
        )
    }
}
