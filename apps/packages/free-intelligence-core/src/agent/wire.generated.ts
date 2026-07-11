/* eslint-disable */
/**
 * DO NOT EDIT — generated from the fi-runner event contract.
 *
 * Source of truth: apps/packages/fi-runner/fi_runner/events.py
 * Schema:          apps/packages/fi-runner/contracts/agent-events.schema.json
 * Regenerate:      pnpm --filter @free-intelligence/core gen:events
 *
 * These are the RAW WIRE frames as fi-runner emits them (snake_case, three
 * envelope shapes). They are NOT the core AgentStreamEvent — that one is the
 * normalized, camelCase contract the reducer consumes. The translation between
 * them lives in the consumer's mapEvent, and now it maps FROM a typed wire
 * frame instead of from `Record<string, unknown>` guesswork.
 */
/**
 * The fi-runner agent stream contract. Generated from fi_runner/events.py — do not edit by hand.
 */
export type AgentStreamEvent =
  | OpenEvent
  | ElementEvent
  | TextEvent
  | ToolCallEvent
  | ResultEvent
  | PlanEvent
  | StepStartedEvent
  | StepDoneEvent
  | StepNotedEvent
  | PlanAmendedEvent
  | PlanCancelledEvent
  | PlanCompletedEvent
  | PlanFailedEvent
  | PlanRejectedEvent
  | ErrorEvent
  | DoneEvent;

/**
 * First frame of every stream. Carries the id a UI keys concurrent turns on.
 */
export interface OpenEvent {
  type?: 'open';
  request_id?: string | null;
}
/**
 * Announces WHO is answering, before any token arrives.
 */
export interface ElementEvent {
  type?: 'element';
  element: ElementPayload;
}
/**
 * Which persona/element answered this turn.
 */
export interface ElementPayload {
  id: string;
  label: string;
}
/**
 * A token delta. Consumers append; they never replace.
 */
export interface TextEvent {
  type?: 'text';
  text: string;
}
export interface ToolCallEvent {
  type?: 'tool_call';
  tool: ToolCallPayload;
}
/**
 * One tool invocation, mirroring :class:`fi_runner.backend.ToolCall`.
 *
 * ``input`` may carry PHI and is never placed in telemetry; it stays on the
 * wire only because the glass-box panel renders it for the operator.
 */
export interface ToolCallPayload {
  name: string;
  server?: string | null;
  input?: {
    [k: string]: unknown;
  } | null;
  id?: string | null;
  is_error?: boolean | null;
  duration_ms?: number | null;
}
export interface ResultEvent {
  type?: 'result';
  result: TurnResultPayload;
}
/**
 * The settled result of a turn, mirroring :class:`fi_runner.backend.TurnResult`.
 */
export interface TurnResultPayload {
  text: string;
  usage?: {
    [k: string]: unknown;
  } | null;
  session_id?: string | null;
  guard_outcomes?: {
    [k: string]: unknown;
  };
  tool_calls?: ToolCallPayload[];
}
/**
 * The agent declared its plan. ``steps`` is the checklist a UI renders.
 */
export interface PlanEvent {
  type?: 'plan';
  data: PlanData;
}
export interface PlanData {
  steps: string[];
  session_id?: string | null;
  request_id?: string | null;
}
export interface StepStartedEvent {
  type?: 'step_started';
  data: StepStartedData;
}
export interface StepStartedData {
  plan_id?: string | null;
  step_index: number;
  request_id?: string | null;
}
export interface StepDoneEvent {
  type?: 'step_done';
  data: StepDoneData;
}
/**
 * ``summary`` accompanies a ``done`` step; ``error`` a failed/cancelled one.
 */
export interface StepDoneData {
  plan_id?: string | null;
  step_index: number;
  status: 'done' | 'failed' | 'cancelled';
  summary?: string | null;
  error?: string | null;
  request_id?: string | null;
}
export interface StepNotedEvent {
  type?: 'step_noted';
  data: StepNotedData;
}
export interface StepNotedData {
  plan_id?: string | null;
  step_index: number;
  note: string;
  request_id?: string | null;
}
export interface PlanAmendedEvent {
  type?: 'plan_amended';
  data: PlanAmendedData;
}
export interface PlanAmendedData {
  plan_id?: string | null;
  action: 'insert' | 'replan';
  request_id?: string | null;
}
export interface PlanCancelledEvent {
  type?: 'plan_cancelled';
  data: PlanCancelledData;
}
export interface PlanCancelledData {
  plan_id?: string | null;
  reason?: string;
  request_id?: string | null;
}
export interface PlanCompletedEvent {
  type?: 'plan_completed';
  data: PlanTerminalData;
}
/**
 * Counters for the terminal plan frame.
 *
 * They default to ``0`` rather than being optional on purpose: a consumer must
 * never receive ``undefined`` here and coerce it silently. The emitter fills
 * real counts whenever the observer ran.
 */
export interface PlanTerminalData {
  plan_id?: string | null;
  completed_count?: number;
  failed_count?: number;
  cancelled_count?: number;
  request_id?: string | null;
}
export interface PlanFailedEvent {
  type?: 'plan_failed';
  data: PlanTerminalData;
}
export interface PlanRejectedEvent {
  type?: 'plan_rejected';
  data: PlanRejectedData;
}
/**
 * A plan guard refused the declared plan before any step ran.
 */
export interface PlanRejectedData {
  reason: string;
  matched?: GuardMatch[];
  reinforcement?: string | null;
  guard?: string | null;
  request_id?: string | null;
}
export interface GuardMatch {
  index: number;
  label: string;
  [k: string]: unknown;
}
/**
 * The turn died. Terminal — no ``done`` follows a fatal error.
 */
export interface ErrorEvent {
  type?: 'error';
  message: string;
}
/**
 * Last frame of a healthy stream.
 */
export interface DoneEvent {
  type?: 'done';
}
