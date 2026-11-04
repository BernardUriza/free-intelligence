import PhotosUI
import SwiftUI
import UIKit
import UniformTypeIdentifiers

/// El «+ Añadir» del riel: Fotos, Cámara o Archivos — las tres puertas que
/// Safari ofrece en el iPhone cuando la web pide una imagen.
struct AdjuntarMenu: View {
    let lugaresLibres: Int
    let onArchivos: ([AdjuntosModel.Archivo]) -> Void

    @State private var seleccion: [PhotosPickerItem] = []
    @State private var mostrandoFotos = false
    @State private var mostrandoCamara = false
    @State private var mostrandoArchivos = false

    var body: some View {
        Menu {
            Button { mostrandoFotos = true } label: { Label("Fotos", systemImage: "photo.on.rectangle") }
            if UIImagePickerController.isSourceTypeAvailable(.camera) {
                Button { mostrandoCamara = true } label: { Label("Tomar foto", systemImage: "camera") }
            }
            Button { mostrandoArchivos = true } label: { Label("Archivos", systemImage: "folder") }
        } label: {
            Image(systemName: "plus")
                .font(.system(size: 18, weight: .medium))
                .foregroundStyle(lugaresLibres > 0 ? Theme.textBody : Theme.textFaint)
                .frame(width: 44, height: 44)
                .contentShape(Rectangle())
        }
        .disabled(lugaresLibres == 0)
        .accessibilityIdentifier("anadir")
        .accessibilityLabel("Añadir")
        .photosPicker(
            isPresented: $mostrandoFotos,
            selection: $seleccion,
            maxSelectionCount: max(1, lugaresLibres),
            matching: .images
        )
        .onChange(of: seleccion) { _, items in
            guard !items.isEmpty else { return }
            seleccion = []
            Task {
                var archivos: [AdjuntosModel.Archivo] = []
                for (indice, item) in items.enumerated() {
                    if let datos = try? await item.loadTransferable(type: Data.self) {
                        archivos.append(.init(datos: datos, nombre: "foto \(indice + 1)"))
                    }
                }
                onArchivos(archivos)
            }
        }
        .fileImporter(
            isPresented: $mostrandoArchivos,
            allowedContentTypes: [.image],
            allowsMultipleSelection: true
        ) { resultado in
            guard case .success(let urls) = resultado else { return }
            let archivos = urls.prefix(max(1, lugaresLibres)).compactMap { url -> AdjuntosModel.Archivo? in
                let acceso = url.startAccessingSecurityScopedResource()
                defer { if acceso { url.stopAccessingSecurityScopedResource() } }
                guard let datos = try? Data(contentsOf: url) else { return nil }
                return .init(datos: datos, nombre: url.lastPathComponent)
            }
            onArchivos(archivos)
        }
        .fullScreenCover(isPresented: $mostrandoCamara) {
            Camara { datos in
                mostrandoCamara = false
                if let datos { onArchivos([.init(datos: datos, nombre: "foto")]) }
            }
            .ignoresSafeArea()
        }
    }
}

/// SwiftUI no trae cámara propia: `UIImagePickerController` es la pieza canónica.
private struct Camara: UIViewControllerRepresentable {
    let alTerminar: (Data?) -> Void

    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController()
        picker.sourceType = .camera
        picker.delegate = context.coordinator
        return picker
    }

    func updateUIViewController(_ controller: UIImagePickerController, context: Context) {}

    func makeCoordinator() -> Coordinador { Coordinador(alTerminar: alTerminar) }

    final class Coordinador: NSObject, UIImagePickerControllerDelegate, UINavigationControllerDelegate {
        let alTerminar: (Data?) -> Void

        init(alTerminar: @escaping (Data?) -> Void) { self.alTerminar = alTerminar }

        func imagePickerController(
            _ picker: UIImagePickerController,
            didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]
        ) {
            let imagen = info[.originalImage] as? UIImage
            alTerminar(imagen?.jpegData(compressionQuality: 0.92))
        }

        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) {
            alTerminar(nil)
        }
    }
}

/// Las imágenes de un mensaje (`MessageImages` de fi-glass): hasta 320pt por
/// lado, radio 12, en una fila que se dobla.
struct ImagenesDelMensaje: View {
    let imagenes: [MessageImage]

    var body: some View {
        FlowFila(espacio: 8) {
            ForEach(Array(imagenes.enumerated()), id: \.offset) { indice, imagen in
                if let ui = UIImage(base64: imagen.data) {
                    let escala = min(1, 320 / max(ui.size.width, 1), 320 / max(ui.size.height, 1))
                    Image(uiImage: ui)
                        .resizable()
                        .frame(width: ui.size.width * escala, height: ui.size.height * escala)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .accessibilityLabel("Imagen adjunta \(indice + 1)")
                }
            }
        }
    }
}

/// Las miniaturas de 56pt sobre el input, cada una con su ✕ de 44pt de área.
struct ChipsDeAdjuntos: View {
    let borradores: [AdjuntosModel.Borrador]
    let deshabilitado: Bool
    let onQuitar: (UUID) -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(borradores) { borrador in
                    ZStack(alignment: .topTrailing) {
                        Group {
                            if let ui = UIImage(base64: borrador.imagen.data) {
                                Image(uiImage: ui).resizable().scaledToFill()
                            } else {
                                Theme.surface
                            }
                        }
                        .frame(width: 56, height: 56)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                        .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.surfaceBorder, lineWidth: 1))
                        Button { onQuitar(borrador.id) } label: {
                            Image(systemName: "xmark")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundStyle(.white)
                                .frame(width: 20, height: 20)
                                .background(Color.black.opacity(0.65), in: Circle())
                                .frame(width: 44, height: 44)
                                .contentShape(Rectangle())
                        }
                        .offset(x: 14, y: -14)
                        .disabled(deshabilitado)
                        .accessibilityLabel("Quitar imagen: \(borrador.nombre)")
                    }
                    .padding(.top, 8)
                    .padding(.trailing, 8)
                }
            }
            .padding(.horizontal, 8)
        }
    }
}

/// Fila que se dobla cuando no cabe, como `flex-wrap` de la web.
private struct FlowFila: Layout {
    let espacio: CGFloat

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let ancho = proposal.width ?? .infinity
        var x: CGFloat = 0, y: CGFloat = 0, alto: CGFloat = 0, maximo: CGFloat = 0
        for vista in subviews {
            let medida = vista.sizeThatFits(.unspecified)
            if x > 0, x + medida.width > ancho { x = 0; y += alto + espacio; alto = 0 }
            x += medida.width + espacio
            alto = max(alto, medida.height)
            maximo = max(maximo, x - espacio)
        }
        return CGSize(width: min(maximo, ancho), height: y + alto)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, alto: CGFloat = 0
        for vista in subviews {
            let medida = vista.sizeThatFits(.unspecified)
            if x > bounds.minX, x + medida.width > bounds.maxX { x = bounds.minX; y += alto + espacio; alto = 0 }
            vista.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(medida))
            x += medida.width + espacio
            alto = max(alto, medida.height)
        }
    }
}

private extension UIImage {
    convenience init?(base64: String) {
        guard let datos = Data(base64Encoded: base64) else { return nil }
        self.init(data: datos)
    }
}
