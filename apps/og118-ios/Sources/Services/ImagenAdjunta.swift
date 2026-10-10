import Foundation
import ImageIO
import UniformTypeIdentifiers

/// `useComposerImages` de fi-glass en nativo: mismos tipos, mismo tope por
/// mensaje, misma reducción (lado 2048, JPEG 0.85) y el mismo techo del base64.
enum ImagenAdjunta {
    static let tiposAceptados: Set<String> = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    static let maximoPorMensaje = 4
    static let bytesSinTocar = 1_500_000
    static let ladoMaximo = 2048
    static let calidadJPEG = 0.85
    static let maximoBase64 = 4 * 1024 * 1024

    enum Rechazo: LocalizedError, Equatable {
        case ilegible(String)
        case muyPesada(String)
        case demasiadas

        var errorDescription: String? {
            switch self {
            case .ilegible(let nombre): return "No se pudo leer la imagen \"\(nombre)\"."
            case .muyPesada(let nombre): return "La imagen \"\(nombre)\" sigue siendo muy pesada después de reducirla."
            case .demasiadas: return "Máximo \(maximoPorMensaje) imágenes por mensaje."
            }
        }
    }

    /// Un archivo chico de tipo aceptado viaja tal cual (el PNG conserva su
    /// transparencia); todo lo demás —HEIC de la cámara incluido— se reduce a JPEG.
    static func preparar(_ datos: Data, nombre: String = "imagen") throws -> MessageImage {
        guard let fuente = CGImageSourceCreateWithData(datos as CFData, nil),
              CGImageSourceGetCount(fuente) > 0 else { throw Rechazo.ilegible(nombre) }
        let mime = (CGImageSourceGetType(fuente) as String?).flatMap { UTType($0)?.preferredMIMEType }
        if let mime, tiposAceptados.contains(mime), datos.count <= bytesSinTocar {
            return MessageImage(mediaType: mime, data: datos.base64EncodedString())
        }
        let opciones: [CFString: Any] = [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceThumbnailMaxPixelSize: ladoMaximo
        ]
        guard let reducida = CGImageSourceCreateThumbnailAtIndex(fuente, 0, opciones as CFDictionary),
              let plana = sobreBlanco(reducida),
              let jpeg = codificarJPEG(plana) else { throw Rechazo.ilegible(nombre) }
        let base64 = jpeg.base64EncodedString()
        guard base64.count <= maximoBase64 else { throw Rechazo.muyPesada(nombre) }
        return MessageImage(mediaType: "image/jpeg", data: base64)
    }

    /// JPEG no tiene alfa: la transparencia se aplana sobre blanco, no sobre negro.
    private static func sobreBlanco(_ imagen: CGImage) -> CGImage? {
        guard let contexto = CGContext(
            data: nil,
            width: imagen.width,
            height: imagen.height,
            bitsPerComponent: 8,
            bytesPerRow: 0,
            space: CGColorSpace(name: CGColorSpace.sRGB)!,
            bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue
        ) else { return nil }
        let marco = CGRect(x: 0, y: 0, width: imagen.width, height: imagen.height)
        contexto.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
        contexto.fill(marco)
        contexto.draw(imagen, in: marco)
        return contexto.makeImage()
    }

    private static func codificarJPEG(_ imagen: CGImage) -> Data? {
        let salida = NSMutableData()
        guard let destino = CGImageDestinationCreateWithData(
            salida, UTType.jpeg.identifier as CFString, 1, nil
        ) else { return nil }
        CGImageDestinationAddImage(
            destino, imagen,
            [kCGImageDestinationLossyCompressionQuality: calidadJPEG] as CFDictionary
        )
        return CGImageDestinationFinalize(destino) ? salida as Data : nil
    }
}
