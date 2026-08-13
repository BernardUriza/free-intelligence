// DO NOT EDIT — generado desde el contrato de eventos de fi-runner.
//
//   apps/packages/fi-runner/fi_runner/events.py
//     -> apps/packages/fi-runner/contracts/agent-events.schema.json
//       -> este archivo   (pnpm --filter @free-intelligence/core gen:swift-events)
//
// Un consumer nativo no puede IMPORTAR el framework, pero el contrato es DATO,
// no código: transcribirlo a mano es lo que hizo que `author` se tipara como
// String y TODA conversación de la web se viera vacía en el teléfono.

import Foundation

enum PlanAmendedDataAction: String, Codable {
    case insert = "insert"
    case replan = "replan"
}

enum StepDoneDataStatus: String, Codable {
    case done = "done"
    case failed = "failed"
    case cancelled = "cancelled"
}

/// Which persona/element answered this turn.
struct ElementPayload: Decodable {
    let id: String
    let label: String
    let name: String?
    let symbol: String?
    let engine: String?

    enum CodingKeys: String, CodingKey {
        case id
        case label
        case name
        case symbol
        case engine
    }
}

struct GuardMatch: Decodable {
    let index: Int
    let label: String

    enum CodingKeys: String, CodingKey {
        case index
        case label
    }
}

struct PlanAmendedData: Decodable {
    let planId: String?
    let action: PlanAmendedDataAction
    let requestId: String?

    enum CodingKeys: String, CodingKey {
        case planId = "plan_id"
        case action
        case requestId = "request_id"
    }
}

struct PlanCancelledData: Decodable {
    let planId: String?
    let reason: String?
    let requestId: String?

    enum CodingKeys: String, CodingKey {
        case planId = "plan_id"
        case reason
        case requestId = "request_id"
    }
}

struct PlanData: Decodable {
    let steps: [String]
    let sessionId: String?
    let requestId: String?

    enum CodingKeys: String, CodingKey {
        case steps
        case sessionId = "session_id"
        case requestId = "request_id"
    }
}

/// A plan guard refused the declared plan before any step ran.
struct PlanRejectedData: Decodable {
    let reason: String
    let matched: [GuardMatch]?
    let reinforcement: String?
    let `guard`: String?
    let requestId: String?

    enum CodingKeys: String, CodingKey {
        case reason
        case matched
        case reinforcement
        case `guard` = "guard"
        case requestId = "request_id"
    }
}

/// Counters for the terminal plan frame.
struct PlanTerminalData: Decodable {
    let planId: String?
    let completedCount: Int?
    let failedCount: Int?
    let cancelledCount: Int?
    let requestId: String?

    enum CodingKeys: String, CodingKey {
        case planId = "plan_id"
        case completedCount = "completed_count"
        case failedCount = "failed_count"
        case cancelledCount = "cancelled_count"
        case requestId = "request_id"
    }
}

/// ``summary`` accompanies a ``done`` step; ``error`` a failed/cancelled one.
struct StepDoneData: Decodable {
    let planId: String?
    let stepIndex: Int
    let status: StepDoneDataStatus
    let summary: String?
    let error: String?
    let requestId: String?

    enum CodingKeys: String, CodingKey {
        case planId = "plan_id"
        case stepIndex = "step_index"
        case status
        case summary
        case error
        case requestId = "request_id"
    }
}

struct StepNotedData: Decodable {
    let planId: String?
    let stepIndex: Int
    let note: String
    let requestId: String?

    enum CodingKeys: String, CodingKey {
        case planId = "plan_id"
        case stepIndex = "step_index"
        case note
        case requestId = "request_id"
    }
}

struct StepStartedData: Decodable {
    let planId: String?
    let stepIndex: Int
    let requestId: String?

    enum CodingKeys: String, CodingKey {
        case planId = "plan_id"
        case stepIndex = "step_index"
        case requestId = "request_id"
    }
}

/// One tool invocation, mirroring :class:`fi_runner.backend.ToolCall`.
struct ToolCallPayload: Decodable {
    let name: String
    let server: String?
    let input: JSONValor?
    let id: String?
    let isError: Bool?
    let durationMs: Int?

    enum CodingKeys: String, CodingKey {
        case name
        case server
        case input
        case id
        case isError = "is_error"
        case durationMs = "duration_ms"
    }
}

/// The settled result of a turn, mirroring :class:`fi_runner.backend.TurnResult`.
struct TurnResultPayload: Decodable {
    let text: String
    let usage: JSONValor?
    let sessionId: String?
    let model: String?
    let guardOutcomes: JSONValor?
    let toolCalls: [ToolCallPayload]?

    enum CodingKeys: String, CodingKey {
        case text
        case usage
        case sessionId = "session_id"
        case model
        case guardOutcomes = "guard_outcomes"
        case toolCalls = "tool_calls"
    }
}

/// Un frame del stream, tal como el contrato lo declara.
enum WireEvent: Decodable {
    case done
    case element(element: ElementPayload)
    case error(message: String)
    case open(requestId: String?)
    case ping
    case plan(data: PlanData)
    case planAmended(data: PlanAmendedData)
    case planCancelled(data: PlanCancelledData)
    case planCompleted(data: PlanTerminalData)
    case planFailed(data: PlanTerminalData)
    case planRejected(data: PlanRejectedData)
    case result(result: TurnResultPayload)
    case stepDone(data: StepDoneData)
    case stepNoted(data: StepNotedData)
    case stepStarted(data: StepStartedData)
    case text(text: String)
    case toolCall(tool: ToolCallPayload)
    /// Un `type` que este build no conoce. NO se descarta: el consumer decide
    /// qué hacer con él, pero nunca desaparece en silencio.
    case desconocido(String)

    private enum CodingKeys: String, CodingKey {
        case type
        case element
        case message
        case requestId = "request_id"
        case data
        case result
        case text
        case tool
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        let tipo = try c.decode(String.self, forKey: .type)
        switch tipo {
        case "done": self = .done
        case "element":
            self = .element(element: try c.decode(ElementPayload.self, forKey: .element))
        case "error":
            self = .error(message: try c.decode(String.self, forKey: .message))
        case "open":
            self = .open(requestId: try c.decodeIfPresent(String.self, forKey: .requestId))
        case "ping": self = .ping
        case "plan":
            self = .plan(data: try c.decode(PlanData.self, forKey: .data))
        case "plan_amended":
            self = .planAmended(data: try c.decode(PlanAmendedData.self, forKey: .data))
        case "plan_cancelled":
            self = .planCancelled(data: try c.decode(PlanCancelledData.self, forKey: .data))
        case "plan_completed":
            self = .planCompleted(data: try c.decode(PlanTerminalData.self, forKey: .data))
        case "plan_failed":
            self = .planFailed(data: try c.decode(PlanTerminalData.self, forKey: .data))
        case "plan_rejected":
            self = .planRejected(data: try c.decode(PlanRejectedData.self, forKey: .data))
        case "result":
            self = .result(result: try c.decode(TurnResultPayload.self, forKey: .result))
        case "step_done":
            self = .stepDone(data: try c.decode(StepDoneData.self, forKey: .data))
        case "step_noted":
            self = .stepNoted(data: try c.decode(StepNotedData.self, forKey: .data))
        case "step_started":
            self = .stepStarted(data: try c.decode(StepStartedData.self, forKey: .data))
        case "text":
            self = .text(text: try c.decode(String.self, forKey: .text))
        case "tool_call":
            self = .toolCall(tool: try c.decode(ToolCallPayload.self, forKey: .tool))
        default: self = .desconocido(tipo)
        }
    }
}
