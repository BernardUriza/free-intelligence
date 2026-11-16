import Foundation

/// Lo último que se vio del servidor, en disco: el hilo y la lista se pintan al
/// instante y se pueden leer sin red. La fuente de verdad sigue siendo el
/// servidor; `pendientes` marca los hilos cuyo último guardado no llegó.
struct CacheLocal {
    let carpeta: URL

    static let viva: CacheLocal = {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        return CacheLocal(carpeta: base.appendingPathComponent("og118-cache", isDirectory: true))
    }()

    func hilo(_ id: String) -> ConversationRecord? {
        leer(ConversationRecord.self, de: archivoDeHilo(id))
    }

    func guardar(_ record: ConversationRecord) {
        escribir(record, en: archivoDeHilo(record.id))
    }

    func olvidar(_ id: String) {
        try? FileManager.default.removeItem(at: archivoDeHilo(id))
        marcarPendiente(id, false)
    }

    func lista() -> [ConversationSummary] {
        leer([ConversationSummary].self, de: carpeta.appendingPathComponent("lista.json")) ?? []
    }

    func guardarLista(_ lista: [ConversationSummary]) {
        escribir(lista, en: carpeta.appendingPathComponent("lista.json"))
    }

    func estaPendiente(_ id: String) -> Bool {
        pendientes().contains(id)
    }

    func marcarPendiente(_ id: String, _ pendiente: Bool) {
        var ids = pendientes()
        guard ids.contains(id) != pendiente else { return }
        if pendiente { ids.insert(id) } else { ids.remove(id) }
        escribir(ids.sorted(), en: archivoDePendientes)
    }

    func vaciar() {
        try? FileManager.default.removeItem(at: carpeta)
    }

    private var archivoDePendientes: URL { carpeta.appendingPathComponent("pendientes.json") }

    private func pendientes() -> Set<String> {
        Set(leer([String].self, de: archivoDePendientes) ?? [])
    }

    private func archivoDeHilo(_ id: String) -> URL {
        let seguro = id.filter { $0.isLetter || $0.isNumber || $0 == "-" }
        return carpeta.appendingPathComponent("hilo-\(seguro).json")
    }

    private func leer<T: Decodable>(_ tipo: T.Type, de archivo: URL) -> T? {
        guard let datos = try? Data(contentsOf: archivo) else { return nil }
        return try? JSONDecoder().decode(tipo, from: datos)
    }

    private func escribir<T: Encodable>(_ valor: T, en archivo: URL) {
        guard let datos = try? JSONEncoder().encode(valor) else { return }
        try? FileManager.default.createDirectory(at: carpeta, withIntermediateDirectories: true)
        try? datos.write(to: archivo, options: .atomic)
    }
}

/// El texto a medio escribir de cada conversación sobrevive a que iOS mate la app.
enum BorradorStore {
    private static let prefijo = "og118.draft."

    static func leer(_ id: String, defaults: UserDefaults = .standard) -> String {
        defaults.string(forKey: prefijo + id) ?? ""
    }

    static func guardar(_ texto: String, _ id: String, defaults: UserDefaults = .standard) {
        if texto.isEmpty {
            defaults.removeObject(forKey: prefijo + id)
        } else {
            defaults.set(texto, forKey: prefijo + id)
        }
    }

    static func vaciar(defaults: UserDefaults = .standard) {
        for llave in defaults.dictionaryRepresentation().keys where llave.hasPrefix(prefijo) {
            defaults.removeObject(forKey: llave)
        }
    }
}
