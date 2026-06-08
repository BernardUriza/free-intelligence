'use client';

/**
 * useOg118Agent — og118's implementation of core's AgentHook.
 *
 * Maps fi-runner's NATIVE stream onto core's AgentStreamEvent union, then feeds
 * the pure `applyAgentEvent` reducer (Berkelio) to build AgentTurnState, which
 * the fi-glass/agent panels render. Same shape as insult_ai mapping its SSE —
 * but og118 maps it from scratch, which is the framework test.
 *
 * Mapping surface (fi-runner → core), documented in VALIDATION_REPORT:
 *   {type:'text', text}                  → {type:'text', delta}
 *   {type:'tool_call', tool:{id,name,server,is_error}} → {type:'tool_call', call:{id,name,server,isError}}
 *   {type:'plan', data:{steps}}          → {type:'plan', steps}
 *   {type:'step_started', data:{step_index}} → {type:'step_started', index}
 *   {type:'step_done', data:{step_index,status,summary?,error?}} → {type:'step_done', index, status, ...}
 *   {type:'result', result:{text,...}}   → {type:'result', text}
 *   open / done                          → pass-through
 *   step_noted / plan_amended / plan_cancelled / plan_completed / plan_failed
 *                                        → mapped (core v1.1.0 models them; the
 *                                          v0 report's "dropped" defect is fixed)
 */

import { useCallback, useRef, useState } from 'react';
import {
  applyAgentEvent,
  initialAgentTurnState,
  type AgentHook,
  type AgentStreamEvent,
  type AgentTurnState,
  type ChatMessage,
} from '@free-intelligence/core';
import { authHeaders, AUTH401 } from './og118Token';
import { makeUserMessage, foldAssistantTurn } from './og118Transcript';

/**
 * og118's hook is an AgentHook (live glass-box turn) PLUS an in-memory
 * conversation transcript (DD-002A). The transcript lives here — not in core —
 * because the stream loop is where the `done` signal that folds a finished turn
 * is unambiguous. messages = completed turns; turn = the live one.
 */
export interface Og118Agent extends AgentHook {
  /** Flat transcript of completed turns (user + assistant), in send order. */
  messages: ChatMessage[];
  /** Clear the whole thread: transcript, live turn, and backend session id. */
  newConversation: () => void;
}

const API = process.env.NEXT_PUBLIC_OG118_API ?? 'http://localhost:8118';

/** fi-runner native frame → core AgentStreamEvent (or null to drop). */
function mapEvent(ev: Record<string, unknown>): AgentStreamEvent | null {
  const data = (ev.data ?? {}) as Record<string, unknown>;
  switch (ev.type) {
    case 'open':
      return { type: 'open' };
    case 'text':
      return { type: 'text', delta: String(ev.text ?? '') };
    case 'tool_call': {
      const t = (ev.tool ?? ev.call ?? {}) as Record<string, unknown>;
      return {
        type: 'tool_call',
        call: {
          id: (t.id as string | null) ?? null,
          name: String(t.name ?? ''),
          server: (t.server as string | null) ?? null,
          isError: (t.is_error as boolean | null) ?? (t.isError as boolean | null) ?? null,
        },
      };
    }
    case 'plan':
      return { type: 'plan', steps: ((data.steps as string[]) ?? []).map(String) };
    case 'plan_rejected':
      return {
        type: 'plan_rejected',
        rejection: {
          reason: String(data.reason ?? ''),
          matched: (data.matched as Array<{ index: number; label: string }>) ?? [],
          guard: (data.guard as string | null) ?? null,
        },
      };
    case 'step_started':
      return { type: 'step_started', index: Number(data.step_index ?? -1) };
    case 'step_done': {
      // core v1.1.0 models 'cancelled' natively — no longer folded to failed.
      const raw = String(data.status ?? 'done');
      const status = raw === 'failed' ? 'failed' : raw === 'cancelled' ? 'cancelled' : 'done';
      return {
        type: 'step_done',
        index: Number(data.step_index ?? -1),
        status,
        summary: data.summary ? String(data.summary) : undefined,
        error: data.error ? String(data.error) : undefined,
      };
    }
    // --- Plan revision & lifecycle (core v1.1.0 — previously dropped) ---
    case 'step_noted':
      return { type: 'step_noted', index: Number(data.step_index ?? -1), note: String(data.note ?? '') };
    case 'plan_amended':
      return { type: 'plan_amended', action: data.action === 'replan' ? 'replan' : 'insert' };
    case 'plan_cancelled':
      return { type: 'plan_cancelled', reason: data.reason ? String(data.reason) : undefined };
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
      const r = (ev.result ?? {}) as Record<string, unknown>;
      return { type: 'result', text: String(r.text ?? '') };
    }
    case 'error':
      return { type: 'error', message: String(ev.message ?? 'error') };
    case 'done':
      return { type: 'done' };
    default:
      return null;
  }
}

export function useOg118Agent(): Og118Agent {
  const [turn, setTurn] = useState<AgentTurnState>(initialAgentTurnState());
  const [isStreaming, setIsStreaming] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const sessionId = useRef<string | null>(null);

  const send = useCallback(async (message: string) => {
    const text = message.trim();
    if (!text || isStreaming) return;

    // Optimistic: the user sees their message the instant they hit send.
    setMessages((prev) => [...prev, makeUserMessage(text)]);

    let state = initialAgentTurnState();
    setTurn(state);
    setIsStreaming(true);
    const apply = (core: AgentStreamEvent | null) => {
      if (!core) return;
      state = applyAgentEvent(state, core);
      setTurn(state);
    };

    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ message: text, session_id: sessionId.current }),
      });
      if (res.status === 401) {
        // Revert the optimistic user message; surface the auth banner (turn=error).
        setMessages((prev) => prev.slice(0, -1));
        apply({ type: 'error', message: `${AUTH401}: token de acceso inválido o ausente` });
        return;
      }
      if (!res.body) throw new Error('no response body');
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split('\n\n');
        buffer = frames.pop() ?? '';
        for (const frame of frames) {
          const line = frame.split('\n').find((l) => l.startsWith('data:'));
          if (!line) continue;
          const ev = JSON.parse(line.slice(5).trim());
          if (ev.type === 'result' && ev.result?.session_id) sessionId.current = ev.result.session_id;
          apply(mapEvent(ev));
        }
      }
      // Turn finished cleanly → fold the answer into the transcript and clear
      // the live area (the answer now lives in `messages`, not `turn`).
      if (state.text) setMessages((prev) => [...prev, foldAssistantTurn(state)]);
      setTurn(initialAgentTurnState());
    } catch (err) {
      // Mid-stream failure: keep the user message in the transcript, show the
      // error on the live turn, do NOT fold (no assistant message, no reset).
      apply({ type: 'error', message: err instanceof Error ? err.message : String(err) });
    } finally {
      setIsStreaming(false);
    }
  }, [isStreaming]);

  // Clears only the live turn (used to dismiss the auth banner) — NOT the transcript.
  const reset = useCallback(() => setTurn(initialAgentTurnState()), []);

  // Explicit "new chat": wipe transcript, live turn, and the backend session id.
  const newConversation = useCallback(() => {
    setMessages([]);
    setTurn(initialAgentTurnState());
    sessionId.current = null;
  }, []);

  return { turn, isStreaming, send, reset, messages, newConversation };
}
