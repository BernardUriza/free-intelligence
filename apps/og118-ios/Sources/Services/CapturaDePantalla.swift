#if os(iOS) && DEBUG
import UIKit

/// Sólo en DEBUG: fotografiar la pantalla del usuario y escupirla por stdout es
/// una capacidad que no tiene por qué existir en un binario que se instala. El
/// launch argument ya la hacía inalcanzable desde el teléfono, pero "difícil de
/// invocar" no es lo mismo que "no está".
///
/// La app se fotografía a sí misma y escupe el PNG en base64 por stdout, que es
/// lo que `devicectl device process launch --console` entrega a la Mac.
///
/// Existe porque NINGUNA herramienta externa puede capturar este teléfono:
/// `idevicescreenshot` y `pymobiledevice3` hablan usbmux, y un iPhone 15 con
/// iOS 26 se conecta por USB-C como INTERFAZ DE RED (en3, IPv6 link-local), no
/// como USB clásico — `ioreg -p IOUSB` y `system_profiler` no lo ven. Xcode lo
/// alcanza por CoreDevice/RemoteXPC, que no expone captura, y `devicectl device
/// stream logs` desapareció en Xcode 26. Lo único que cruza es stdout.
enum CapturaDePantalla {
    /// Trozos de 1500 para que ninguna línea se pierda por límites de buffer.
    private static let trozo = 1500

    @MainActor
    static func emitir(_ etiqueta: String) {
        guard let ventana = UIApplication.shared.connectedScenes
            .compactMap({ $0 as? UIWindowScene })
            .flatMap({ $0.windows })
            .first(where: \.isKeyWindow) else {
            print("[captura] sin ventana visible")
            return
        }
        let render = UIGraphicsImageRenderer(bounds: ventana.bounds)
        let imagen = render.image { _ in
            // drawHierarchy captura la jerarquía REAL compuesta; layer.render
            // se pierde efectos y contenido de SwiftUI.
            ventana.drawHierarchy(in: ventana.bounds, afterScreenUpdates: true)
        }
        guard let png = imagen.pngData() else {
            print("[captura] no se pudo codificar el PNG")
            return
        }
        let texto = png.base64EncodedString()
        print("[captura] inicio \(etiqueta) bytes=\(png.count) partes=\((texto.count + trozo - 1) / trozo)")
        var indice = texto.startIndex
        var n = 0
        while indice < texto.endIndex {
            let fin = texto.index(indice, offsetBy: trozo, limitedBy: texto.endIndex) ?? texto.endIndex
            print("[b64:\(n)] \(texto[indice..<fin])")
            indice = fin
            n += 1
        }
        print("[captura] fin \(etiqueta)")
    }
}
#endif
