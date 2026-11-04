/**
 * fi-runner wire frame → core {@link AgentStreamEvent}, or null to drop it.
 *
 * The wire is `contracts/agent-events.schema.json`; the app-level event is what
 * {@link applyAgentEvent} reduces. This mapping lived in og118's transport hook
 * and every other consumer of the stream (the iPhone, the next shell) had to
 * rewrite it. It is substrate: one mapping, checked against the same vectors
 * the native client replays (`contracts/agent-turn.vectors.json`).
 *
 * @param frame one decoded SSE `data:` payload
 * @returns the core event, or null for a frame this layer has no use for
 */
import type { AgentStreamEvent } from './events';

type Raw = Record<string, unknown>;

function rec(v: unknown): Raw {
  return v && typeof v === 'object' ? (v as Raw) : {};
}

function str(v: unknown, fallback = ''): string {
  return v == null ? fallback : String(v);
}

function nullableStr(v: unknown): string | null {
  return typeof v === 'string' && v.trim() ? v : null;
}

export function fromWireEvent(frame: unknown): AgentStreamEvent | null {
  const ev = rec(frame);
  const data = rec(ev.data);
  switch (ev.type) {
    case 'open':
      return { type: 'open' };
    case 'text':
      return { type: 'text', delta: str(ev.text) };
    case 'element': {
      const el = rec(ev.element);
      const id = str(el.id);
      if (!id) return null;
      return {
        type: 'author',
        author: {
          id,
          name: str(el.name) || str(el.label) || id,
          symbol: (el.symbol as string | null) ?? null,
          engine: (el.engine as string | null) ?? null,
        },
      };
    }
    case 'tool_call': {
      const t = rec(ev.tool ?? ev.call);
      return {
        type: 'tool_call',
        call: {
          id: (t.id as string | null) ?? null,
          name: str(t.name),
          server: (t.server as string | null) ?? null,
          isError: (t.is_error as boolean | null) ?? (t.isError as boolean | null) ?? null,
        },
      };
    }
    case 'plan':
      return { type: 'plan', steps: ((data.steps as unknown[]) ?? []).map((s) => str(s)) };
    case 'plan_rejected':
      return {
        type: 'plan_rejected',
        rejection: {
          reason: str(data.reason),
          matched: (data.matched as Array<{ index: number; label: string }>) ?? [],
          guard: (data.guard as string | null) ?? null,
        },
      };
    case 'step_started':
      return { type: 'step_started', index: Number(data.step_index ?? -1) };
    case 'step_done': {
      const raw = str(data.status, 'done');
      const status = raw === 'failed' ? 'failed' : raw === 'cancelled' ? 'cancelled' : 'done';
      return {
        type: 'step_done',
        index: Number(data.step_index ?? -1),
        status,
        summary: data.summary ? str(data.summary) : undefined,
        error: data.error ? str(data.error) : undefined,
      };
    }
    case 'step_noted':
      return { type: 'step_noted', index: Number(data.step_index ?? -1), note: str(data.note) };
    case 'plan_amended':
      return { type: 'plan_amended', action: data.action === 'replan' ? 'replan' : 'insert' };
    case 'plan_cancelled':
      return { type: 'plan_cancelled', reason: data.reason ? str(data.reason) : undefined };
    case 'plan_completed':
      return {
        type: 'plan_completed',
        completedCount: Number(data.completed_count ?? 0),
        failedCount: Number(data.failed_count ?? 0),
        cancelledCount: Number(data.cancelled_count ?? 0),
      };
    case 'plan_failed':
      return {
        type: 'plan_failed',
        completedCount: Number(data.completed_count ?? 0),
        failedCount: Number(data.failed_count ?? 0),
        cancelledCount: Number(data.cancelled_count ?? 0),
      };
    case 'result': {
      const r = rec(ev.result);
      const model = nullableStr(r.model);
      const reactions = Array.isArray(r.reactions)
        ? r.reactions.map((x) => str(x).trim()).filter(Boolean)
        : [];
      return {
        type: 'result',
        text: str(r.text),
        ...(model ? { meta: { model } } : {}),
        ...(reactions.length > 0 ? { reactions } : {}),
      };
    }
    case 'error':
      return { type: 'error', message: str(ev.message, 'error') };
    case 'ping':
      return { type: 'ping' };
    case 'deferred':
      return { type: 'deferred' };
    case 'done':
      return { type: 'done' };
    default:
      return null;
  }
}
