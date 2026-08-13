import Foundation

struct Element: Codable, Identifiable {
    let id: String
    let atomicNumber: Int
    let symbol: String
    let slug: String
    let displayName: String
    let displayLabel: String
    let engine: String?
    let description: String?

    /// El token que `/chat/stream` resuelve contra el registry. El slug es la
    /// forma canónica que el servidor documenta; símbolo y número también
    /// resuelven, pero el slug no colisiona.
    var token: String { slug }
}

struct ElementList: Codable {
    let elements: [Element]
}

struct Project: Codable, Identifiable {
    let id: String
    let name: String
    let createdAt: String?
}

struct ProjectList: Codable {
    let projects: [Project]
}

/// El elemento y el proyecto activos sobreviven al cierre de la app: si eliges
/// hablar con Yodo, reabrir no debe devolverte al companion base en silencio.
enum TurnContextStore {
    private static let elementKey = "og118.active.element"
    private static let corpusKey = "og118.active.corpus"

    static func loadElement(defaults: UserDefaults = .standard) -> String? {
        defaults.string(forKey: elementKey)
    }

    static func saveElement(_ token: String?, defaults: UserDefaults = .standard) {
        if let token, !token.isEmpty {
            defaults.set(token, forKey: elementKey)
        } else {
            defaults.removeObject(forKey: elementKey)
        }
    }

    static func loadCorpus(defaults: UserDefaults = .standard) -> String? {
        defaults.string(forKey: corpusKey)
    }

    static func saveCorpus(_ id: String?, defaults: UserDefaults = .standard) {
        if let id, !id.isEmpty {
            defaults.set(id, forKey: corpusKey)
        } else {
            defaults.removeObject(forKey: corpusKey)
        }
    }
}

@MainActor
final class CatalogModel: ObservableObject {
    @Published private(set) var elements: [Element] = []
    @Published private(set) var projects: [Project] = []
    @Published var errorMessage: String?

    typealias LoadElements = () async throws -> [Element]
    typealias LoadProjects = () async throws -> [Project]

    private let loadElements: LoadElements
    private let loadProjects: LoadProjects

    init(loadElements: @escaping LoadElements, loadProjects: @escaping LoadProjects) {
        self.loadElements = loadElements
        self.loadProjects = loadProjects
    }

    convenience init(client: Og118Client) {
        self.init(loadElements: client.listElements, loadProjects: client.listProjects)
    }

    func refresh() async {
        do {
            elements = try await loadElements()
        } catch {
            errorMessage = error.localizedDescription
        }
        do {
            projects = try await loadProjects()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func elementName(for token: String?) -> String {
        guard let token else { return "og118" }
        return elements.first { $0.token == token }?.displayName ?? token
    }

    func projectName(for id: String?) -> String? {
        guard let id else { return nil }
        return projects.first { $0.id == id }?.name ?? id
    }
}
