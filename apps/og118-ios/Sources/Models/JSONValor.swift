import Foundation

/// Un valor JSON cualquiera, para poder ARRASTRAR campos que esta versión no
/// modela sin entenderlos. Sin esto, cada `save()` reescribe el record desde
/// una struct reducida y AMPUTA todo lo demás: un chat de la web con imágenes
/// las perdía para siempre en cuanto contestabas un mensaje desde el teléfono.
enum JSONValor: Codable, Equatable {
    case nulo
    case bool(Bool)
    case numero(Double)
    case texto(String)
    case lista([JSONValor])
    case objeto([String: JSONValor])

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .nulo; return }
        if let v = try? c.decode(Bool.self) { self = .bool(v); return }
        if let v = try? c.decode(Double.self) { self = .numero(v); return }
        if let v = try? c.decode(String.self) { self = .texto(v); return }
        if let v = try? c.decode([JSONValor].self) { self = .lista(v); return }
        if let v = try? c.decode([String: JSONValor].self) { self = .objeto(v); return }
        throw DecodingError.dataCorruptedError(in: c, debugDescription: "JSON no reconocido")
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .nulo: try c.encodeNil()
        case .bool(let v): try c.encode(v)
        case .numero(let v): try c.encode(v)
        case .texto(let v): try c.encode(v)
        case .lista(let v): try c.encode(v)
        case .objeto(let v): try c.encode(v)
        }
    }
}

/// Llave dinámica: los campos ajenos no se conocen en tiempo de compilación.
struct LlaveLibre: CodingKey {
    let stringValue: String
    var intValue: Int? { nil }
    init(stringValue: String) { self.stringValue = stringValue }
    init?(intValue: Int) { nil }
}
