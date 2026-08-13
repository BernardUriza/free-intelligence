import Foundation

enum StreamEvent {
    case open
    case text(String)
    case author(id: String, name: String)
    case toolCall(name: String, server: String?, isError: Bool)
    case result(text: String, model: String?)
    case done
    case failure(String)
    /// El plan del agente y sus pasos. Sin estos casos los frames llegaban,
    /// se decodificaban y se tiraban: en pantalla no quedaba rastro de que el
    /// agente estuviera trabajando.
    case plan([String])
    case stepStarted(Int)
    case stepDone(index: Int, status: StepStatus, summary: String?, error: String?)
    case stepNoted(index: Int, note: String)
    case unmapped(String)
}

private struct ElementFrame: Decodable {
    let id: String?
    let name: String?
    let label: String?
}

private struct ToolFrame: Decodable {
    let name: String?
    let server: String?
    let isError: Bool?

    enum CodingKeys: String, CodingKey {
        case name, server
        case isError = "is_error"
    }
}

private struct ResultFrame: Decodable {
    let text: String?
    let model: String?
}

enum StepStatus: String {
    case done
    case failed
    case cancelled
}

private struct PlanData: Decodable {
    let steps: [String]?
    let stepIndex: Int?
    let status: String?
    let summary: String?
    let error: String?
    let note: String?

    enum CodingKeys: String, CodingKey {
        case steps, status, summary, error, note
        case stepIndex = "step_index"
    }
}

private struct RawFrame: Decodable {
    let type: String
    let text: String?
    let message: String?
    let element: ElementFrame?
    let tool: ToolFrame?
    let result: ResultFrame?
    let data: PlanData?
}

extension StreamEvent {
    static func decode(_ payload: Data) -> StreamEvent? {
        guard let raw = try? JSONDecoder().decode(RawFrame.self, from: payload) else { return nil }
        switch raw.type {
        case "open":
            return .open
        case "text":
            return .text(raw.text ?? "")
        case "element":
            guard let element = raw.element, let id = element.id, !id.isEmpty else { return nil }
            let name = element.name.flatMap { $0.isEmpty ? nil : $0 }
                ?? element.label.flatMap { $0.isEmpty ? nil : $0 }
                ?? id
            return .author(id: id, name: name)
        case "tool_call":
            guard let tool = raw.tool else { return nil }
            return .toolCall(name: tool.name ?? "", server: tool.server, isError: tool.isError ?? false)
        case "result":
            return .result(text: raw.result?.text ?? "", model: raw.result?.model)
        case "plan":
            return .plan(raw.data?.steps ?? [])
        case "step_started":
            return .stepStarted(raw.data?.stepIndex ?? -1)
        case "step_done":
            return .stepDone(
                index: raw.data?.stepIndex ?? -1,
                status: StepStatus(rawValue: raw.data?.status ?? "done") ?? .done,
                summary: raw.data?.summary,
                error: raw.data?.error
            )
        case "step_noted":
            return .stepNoted(index: raw.data?.stepIndex ?? -1, note: raw.data?.note ?? "")
        case "done":
            return .done
        case "error":
            return .failure(raw.message ?? "error")
        default:
            return .unmapped(raw.type)
        }
    }
}
