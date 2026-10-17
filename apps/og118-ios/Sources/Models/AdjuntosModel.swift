import Foundation

/// Las imágenes del mensaje que se está escribiendo: se validan y reducen al
/// entrar, con el tope y los mensajes de rechazo de la web.
@MainActor
final class AdjuntosModel: ObservableObject {
    struct Borrador: Identifiable {
        let id = UUID()
        let imagen: MessageImage
        let nombre: String
    }

    struct Archivo {
        let datos: Data
        let nombre: String
    }

    @Published private(set) var borradores: [Borrador] = []
    @Published private(set) var procesando = false
    @Published var error: String?

    var imagenes: [MessageImage] { borradores.map(\.imagen) }
    var lugaresLibres: Int { max(0, ImagenAdjunta.maximoPorMensaje - borradores.count) }

    func agregar(_ archivos: [Archivo]) async {
        procesando = true
        defer { procesando = false }
        for archivo in archivos {
            guard borradores.count < ImagenAdjunta.maximoPorMensaje else {
                error = ImagenAdjunta.Rechazo.demasiadas.errorDescription
                return
            }
            do {
                let imagen = try await Task.detached(priority: .userInitiated) {
                    try ImagenAdjunta.preparar(archivo.datos, nombre: archivo.nombre)
                }.value
                borradores.append(Borrador(imagen: imagen, nombre: archivo.nombre))
            } catch {
                self.error = (error as? LocalizedError)?.errorDescription ?? error.localizedDescription
            }
        }
    }

    func quitar(_ id: UUID) {
        borradores.removeAll { $0.id == id }
    }

    func vaciar() {
        borradores = []
    }

    /// Las imágenes de un turno que falló vuelven al composer con el texto.
    func restaurar(_ imagenes: [MessageImage]) {
        borradores = imagenes.map { Borrador(imagen: $0, nombre: "imagen") }
    }
}
