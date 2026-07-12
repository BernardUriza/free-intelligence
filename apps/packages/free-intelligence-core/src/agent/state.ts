/**
 * AgentTurnState — the reduced state the fi-glass agent panels render, plus the
 * pure `applyAgentEvent` reducer that derives it from the wire stream.
 *
 * The reducer is pure (no React, no transport, no I/O) so every app reuses the
 * same event→state logic and only supplies the transport that produces the
 * AgentStreamEvent stream. Immutable: every event returns a new state object.
 */

import type {
  AgentStreamEvent,
  AgentMeta,
  GuardRejection,
  MessageAuthor,
  ToolCall,
  StepStatus,
} from './events';

/** One step of the declared plan, enriched with live status. */
export interface PlanStep {
  label: string;
  status: StepStatus;
  summary?: string;
  error?: string;
  /** Free-text annotation from note_step (carried by the step_noted event). */
  note?: string;
}

/** Terminal verdict of a whole plan (finalize_plan / cancel_plan). */
export type PlanOutcome = 'completed' | 'failed' | 'cancelled';

/** The agent's declared plan. Guard-as-quality: rejection is woven in here. */
export interface AgentPlan {
  steps: PlanStep[];
  /** Set when a guard blocks; cleared when a fresh plan is declared. */
  rejection?: GuardRejection | null;
  /**
   * Set when the agent restructures the plan mid-turn (plan_amended). 'replan'
   * is then followed by a fresh `plan` event that reseeds steps and clears this.
   */
  amended?: 'insert' | 'replan' | null;
  /** Terminal plan verdict once finalize_plan / cancel_plan settles it. */
  outcome?: PlanOutcome | null;
}

export type AgentTurnStatus = 'thinking' | 'streaming' | 'done' | 'error';

/** The full reduced state of one agentic turn. */
export interface AgentTurnState {
  plan: AgentPlan | null;
  steps: ToolCall[];
  text: string;
  /** Evidence references (e.g. source URLs). App-agnostic name. */
  sources: string[];
  meta: AgentMeta | null;
  /**
   * WHO is answering this turn, once the backend announces it (`author` event).
   * null means the backend never named a speaker — the shell then attributes the
   * turn to the agent's default author, which it must supply. See
   * {@link MessageAuthor}.
   */
  author: MessageAuthor | null;
  /**
   * How many signs of life the backend has sent while the turn was QUIET (bare
   * `ping` frames). A shell's idle watchdog re-arms on this: a healthy turn can
   * be silent for a long time (a proxied engine answers in one shot; a model
   * thinks before its first token), and killing it throws away what the user
   * wrote. A counter, not a timestamp — the reducer stays pure.
   */
  heartbeats: number;
  status: AgentTurnStatus;
  errorMessage?: string;
}

/** A fresh, empty turn — call at the start of each agentic turn. */
export function initialAgentTurnState(): AgentTurnState {
  return {
    plan: null,
    steps: [],
    text: '',
    sources: [],
    meta: null,
    author: null,
    heartbeats: 0,
    status: 'thinking',
  };
}

/**
 * Pure reducer: apply one wire event to the turn state, returning a new state.
 *
 * Mirrors the universal turn lifecycle; an app's hook feeds it the events its
 * transport produces. Unknown/transport-only events (`open`) pass through
 * untouched.
 */
export function applyAgentEvent(
  state: AgentTurnState,
  event: AgentStreamEvent
): AgentTurnState {
  // Bump 'thinking' → 'streaming' on the first sign of activity; never regress
  // a settled ('done'/'error') turn. Mirrors the original's status moves but is
  // guarded against out-of-order events.
  const streamingStatus: AgentTurnStatus =
    state.status === 'thinking' ? 'streaming' : state.status;

  switch (event.type) {
    case 'open':
      return state;

    case 'plan':
      // A fresh plan seeds N steps as 'pending' (index i ↔ step i) and clears
      // any prior guard rejection (the agent is re-declaring).
      return {
        ...state,
        plan: {
          steps: event.steps.map((label) => ({ label, status: 'pending' })),
          rejection: null,
          amended: null,
          outcome: null,
        },
        status: streamingStatus,
      };

    case 'plan_rejected':
      return state.plan
        ? { ...state, plan: { ...state.plan, rejection: event.rejection } }
        : { ...state, plan: { steps: [], rejection: event.rejection } };

    case 'step_started': {
      if (!state.plan) return state;
      const idx = event.index;
      if (idx < 0 || idx >= state.plan.steps.length) return state; // bounds guard
      // Catch-up sweep: starting step N implies steps 0..N-1 finished, even if
      // their step_done events were dropped (SSE is lossy). Then mark N running.
      const steps = state.plan.steps.map((s, i) => {
        if (i < idx && (s.status === 'pending' || s.status === 'running')) {
          return { ...s, status: 'done' as const };
        }
        if (i === idx) return { ...s, status: 'running' as const };
        return s;
      });
      return { ...state, plan: { ...state.plan, steps } };
    }

    case 'step_done': {
      if (!state.plan) return state;
      const idx = event.index;
      if (idx < 0 || idx >= state.plan.steps.length) return state; // bounds guard
      const steps = state.plan.steps.map((s, i) => {
        if (i !== idx) return s; // mutate exactly step N — no off-by-one
        const patch: PlanStep = { ...s, status: event.status };
        // 'done' carries a summary; 'failed'/'cancelled' carry a reason in error.
        if (event.status === 'done') {
          if (event.summary) patch.summary = event.summary;
        } else if (event.error) {
          patch.error = event.error;
        }
        return patch;
      });
      return { ...state, plan: { ...state.plan, steps } };
    }

    case 'step_noted': {
      // Annotate exactly step N with a free-text note; never touches status.
      if (!state.plan) return state;
      const idx = event.index;
      if (idx < 0 || idx >= state.plan.steps.length) return state; // bounds guard
      const steps = state.plan.steps.map((s, i) =>
        i === idx ? { ...s, note: event.note } : s
      );
      return { ...state, plan: { ...state.plan, steps } };
    }

    case 'plan_amended':
      // Record that the plan was restructured. For 'replan' the new steps land
      // in a following `plan` event (which clears this flag); here we only set
      // the badge signal — the amended event carries no steps to apply.
      return state.plan
        ? { ...state, plan: { ...state.plan, amended: event.action } }
        : state;

    case 'plan_cancelled': {
      // The whole plan was abandoned. Settle still-open steps as 'cancelled'
      // (NOT 'done' — distinct from the `result` close-out sweep, which only
      // touches pending/running and would wrongly mark these done if it ran
      // after us). Already-settled steps keep their terminal status.
      if (!state.plan) return state;
      const steps = state.plan.steps.map((s) =>
        s.status === 'pending' || s.status === 'running'
          ? { ...s, status: 'cancelled' as const }
          : s
      );
      return { ...state, plan: { ...state.plan, steps, outcome: 'cancelled' } };
    }

    case 'plan_completed':
      // Terminal verdict. Per-step statuses already reflect reality (each
      // step_done settled them); we only stamp the plan-level outcome. The
      // wire counts are derivable from steps[].status, so we don't store them.
      return state.plan
        ? { ...state, plan: { ...state.plan, outcome: 'completed' } }
        : state;

    case 'plan_failed':
      // Plan failed (>=1 step failed). Leave step statuses as settled — a
      // failed plan can still have done steps — and stamp the outcome.
      return state.plan
        ? { ...state, plan: { ...state.plan, outcome: 'failed' } }
        : state;

    case 'tool_call': {
      // Dedupe-on-arrival by id (DELIBERATE divergence from the original's
      // append + replace-at-result, since the contract's `result` carries no
      // tool_calls). id == null = still pending → append.
      const existing =
        event.call.id != null
          ? state.steps.findIndex((c) => c.id === event.call.id)
          : -1;
      const steps =
        existing >= 0
          ? state.steps.map((c, i) => (i === existing ? event.call : c))
          : [...state.steps, event.call];
      return { ...state, steps, status: streamingStatus };
    }

    case 'text':
      // CONCATENATE deltas (never replace) — the streaming bug that compiles
      // identically but only shows the last fragment at runtime.
      return {
        ...state,
        text: state.text + event.delta,
        status: streamingStatus,
      };

    case 'result': {
      // Never wipe a non-empty streamed accumulation with an empty result.text
      // (the agent ran tools but composed no final response). Note: app-specific
      // dedupe/source-extraction stays in the app's hook, which emits
      // `sources` already extracted.
      const text = event.text.trim() ? event.text : state.text;
      // Close any plan steps left open when the turn settles.
      const plan = state.plan
        ? {
            ...state.plan,
            steps: state.plan.steps.map((s) =>
              s.status === 'pending' || s.status === 'running'
                ? { ...s, status: 'done' as const }
                : s
            ),
          }
        : state.plan;
      return {
        ...state,
        text,
        plan,
        sources: event.sources ?? state.sources,
        meta: event.meta ?? state.meta,
        status: 'done',
      };
    }

    case 'author':
      return { ...state, author: event.author };

    case 'ping':
      // Carries nothing; its ARRIVAL is the payload. A NEW object every time, on
      // purpose: that is what tells a watchdog watching this turn to re-arm.
      return { ...state, heartbeats: state.heartbeats + 1 };

    case 'meta':
      return { ...state, meta: event.meta };

    case 'error':
      return { ...state, status: 'error', errorMessage: event.message };

    case 'done':
      return state.status === 'thinking' || state.status === 'streaming'
        ? { ...state, status: 'done' }
        : state;

    default:
      return state;
  }
}
