/**
 * AgentStreamEvent — the agent-turn wire contract.
 *
 * Material-agnostic, React-free, and intentionally NOT shaped to any one app's
 * backend. Each app's hook MAPS its real stream onto this union: insult_ai maps
 * its `/chat/stream` SSE frames; og118 maps its own transport; a fi-runner-native
 * hook would map `turn_flow` / `ToolCall` / task_tracker stream events. The
 * fi-glass agent panels and the pure `applyAgentEvent` reducer consume ONLY this
 * union — never a concrete transport, endpoint, or auth.
 *
 * This is the neutral middle: it equals neither insult_ai's frontend shape nor
 * fi-core's task_tracker shape; both map onto it. It is the most consequential
 * contract in the fi-glass roadmap — og118 and every future app inherit it.
 */

/** Lifecycle status of a single planned step. */
export type StepStatus = 'pending' | 'running' | 'done' | 'failed' | 'cancelled';

/** Severity a guard can assign. Generic — each app names its own guards. */
export type GuardLevel = 'ok' | 'warning' | 'critical';

/** A tool invocation surfaced for the live audit trail. */
export interface ToolCall {
  /** Stable id from the provider (e.g. tool_use_id); null while pending. */
  id: string | null;
  /** Tool identifier as the agent named it. */
  name: string;
  /** Originating server/namespace, or null for built-ins. */
  server: string | null;
  /** null = pending, false = ok, true = errored. */
  isError: boolean | null;
}

/**
 * A soft guard decision against the declared plan (the stream continues).
 *
 * Core defines the SHAPE of the verdict — not what any guard evaluates. The
 * `reason`/copy is owned by the app; core only carries that a guardrail
 * assessed the plan and emitted a verdict. This is the universal agentic-safety
 * pattern, not a domain concept.
 */
export interface GuardRejection {
  /** Human-readable reason. App owns the wording/copy. */
  reason: string;
  /** Which plan steps tripped the guard. */
  matched: Array<{ index: number; label: string }>;
  /** Guard identifier (app-defined), or null. */
  guard: string | null;
}

/**
 * MessageAuthor — WHO produced a message. Part of the contract, not app wiring.
 *
 * A shell that lets the user switch the answering persona (og118's elementos,
 * aurity's personas) renders a transcript where every bubble must say who spoke;
 * an assistant bubble with no author silently attributes the answer to the app
 * itself. That is a lie the framework must not be able to express — so the fold
 * ({@link foldAssistantTurn}) and the user capsule ({@link makeUserMessage})
 * both REQUIRE an author, and a turn can rebind it mid-stream via the `author`
 * event (the backend announces the persona it resolved for the turn).
 *
 * Only `id` and `name` are load-bearing; `symbol` and `engine` are optional
 * enrichment a shell may render as an avatar token / provenance chip.
 */
export interface MessageAuthor {
  /** Stable identifier of the speaker (element id, persona id, 'user'). */
  id: string;
  /** Human name shown as the author ("Yodo", "og118", "Tú"). */
  name: string;
  /** Short avatar/badge token ("I", "og"). */
  symbol?: string | null;
  /** The engine/persona behind the answer ("Vultur", "ALICE"). */
  engine?: string | null;
}

/** Per-turn observability. All optional; each app fills what it has. */
export interface AgentMeta {
  requestId?: string | null;
  latencyMs?: number | null;
  toolCount?: number | null;
  tokens?: Record<string, unknown> | null;
  /** Worst-case guard verdicts by guard name. */
  guardLevels?: Record<string, GuardLevel> | null;
  attempts?: number | null;
  model?: string | null;
}

/**
 * The discriminated union an app's hook emits as a turn unfolds.
 *
 * `plan` carries flat labels (the initial announcement, no status yet); the rich
 * per-step state (PlanStep) is built by the reducer as `step_started`/`step_done`
 * arrive — the separation between "what was announced" and "what has happened".
 *
 * `result.sources` is the generic name for evidence references (e.g. source URLs
 * from RAG or web-search). Apps extract them however they like (insult_ai parses
 * a "Receipts" markdown tail in its own hook — app-specific, stays there).
 */
export type AgentStreamEvent =
  | { type: 'open'; sessionId?: string; requestId?: string }
  | { type: 'plan'; steps: string[] }
  | { type: 'plan_rejected'; rejection: GuardRejection }
  | { type: 'step_started'; index: number }
  | {
      type: 'step_done';
      index: number;
      status: 'done' | 'failed' | 'cancelled';
      summary?: string;
      error?: string;
    }
  // --- Plan revision & lifecycle ------------------------------------------
  // Faithful to fi-runner's task_tracker stream (see fi_runner/_plan_events.py).
  // Without these variants an app's hook DROPS the signal (og118 did exactly
  // that) — the turn re-plans or cancels and the UI never learns.
  //
  // A step gained a free-text annotation (note_step). Carries the note so the
  // UI can show WHY, not merely that a note exists.
  | { type: 'step_noted'; index: number; note: string }
  // The agent restructured the plan mid-turn: 'insert' splices a step in;
  // 'replan' replaces the plan (its new steps arrive in a fresh `plan` event,
  // which clears the amended flag). The amended event itself carries no steps.
  | { type: 'plan_amended'; action: 'insert' | 'replan' }
  // The whole plan was abandoned (cancel_plan). `reason` is on the wire even
  // though the reducer doesn't surface it yet — the contract equals the wire.
  | { type: 'plan_cancelled'; reason?: string }
  // Terminal plan verdicts (finalize_plan). Counts are derivable from
  // steps[].status, but the backend's authoritative tallies ride the wire too
  // (they survive lossy SSE that the per-step events may not).
  | {
      type: 'plan_completed';
      completedCount?: number;
      failedCount?: number;
      cancelledCount?: number;
    }
  | {
      type: 'plan_failed';
      completedCount?: number;
      failedCount?: number;
      cancelledCount?: number;
    }
  | { type: 'tool_call'; call: ToolCall }
  | { type: 'text'; delta: string }
  // The backend resolved WHO answers this turn (a persona/element the user
  // selected). Emitted before the first text delta, so the live bubble is
  // attributed from its first character — not re-labelled after the fold.
  | { type: 'author'; author: MessageAuthor }
  | { type: 'result'; text: string; sources?: string[]; meta?: AgentMeta }
  | { type: 'meta'; meta: AgentMeta }
  | { type: 'error'; message: string }
  | { type: 'done' };
