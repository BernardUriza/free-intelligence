'use client';

/**
 * useOg118Agent — og118's implementation of core's AgentHook (the TRANSPORT).
 *
 * Maps fi-runner's NATIVE stream onto core's AgentStreamEvent union, then feeds
 * the pure `applyAgentEvent` reducer (Berkelio) to build the live AgentTurnState.
 * This hook owns ONE live turn — the conversation transcript is NOT here. The
 * visible thread (user message, assistant fold, transcript) is the framework's
 * job: fi-glass `useAgentConversation` wraps this hook (DD-002-LESSON — the
 * reusable primitive lives in the framework, not the consumer).
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
 *                                        → mapped (core v1.1.0 models them)
 */

import { useCallback, useRef, useState } from 'react';
import {
  applyAgentEvent,
  initialAgentTurnState,
  type AgentHook,
  type AgentSendMeta,
  type AgentStreamEvent,
  type AgentTurnState,
} from '@free-intelligence/core';
import { authHeaders, AUTH401 } from './og118Token';

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
    // --- Plan revision & lifecycle (core v1.1.0) ---
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

export function useOg118Agent(
  sessionId: string | null,
  activeCorpusId: string | null = null,
  activeElement: string | null = null,
): AgentHook {
  const [turn, setTurn] = useState<AgentTurnState>(initialAgentTurnState());
  const [isStreaming, setIsStreaming] = useState(false);
  // DD-002B1.3: the active conversation id is owned by the conversation library
  // (fi-glass `useConversationLibrary`) and passed IN — it IS the backend
  // session_id, so the local transcript and the server's conversation store key
  // one thread. A ref keeps the stable `send()` closure reading the CURRENT id
  // after a chat switch (the active id changes without recreating send).
  const sessionIdRef = useRef<string | null>(sessionId);
  sessionIdRef.current = sessionId;
  // proj-corpusbind: the active project's corpus, read by the stable send()
  // closure at call time (like sessionId). When set, it scopes the agent's
  // rag_store search to that corpus this turn; null → no active project.
  const corpusIdRef = useRef<string | null>(activeCorpusId);
  corpusIdRef.current = activeCorpusId;
  // OG118-ELEMENTS-SELECTOR: the active "elemento" slug, read by the stable send()
  // closure at call time (like corpusId). When set, the backend registry resolves
  // it and swaps the answering persona this turn; '' / null → base og118 persona.
  const elementRef = useRef<string | null>(activeElement);
  elementRef.current = activeElement;
  // B3-FIGLASS-8: the in-flight request, so the framework's turn-timeout watchdog
  // (useAgentConversation) can actually CANCEL the network call via abort() — not
  // just drop the UI out of streaming. Without this the timed-out fetch would leak.
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(async (message: string, meta?: AgentSendMeta) => {
    const text = message.trim();
    if (!text || isStreaming) return;
    const sid = sessionIdRef.current;
    if (!sid) return; // no active conversation yet — controlled no-op

    // og118 is local-first: the durable transcript lives in the browser (IndexedDB
    // via useConversationLibrary). We replay the confirmed thread on each turn so
    // continuity survives a recycled/redeployed backend with NO server-side store.
    // Send ONLY role/content — never ids, timestamps, tool payloads, or audio
    // metadata (privacy + the backend treats it as untrusted context, not auth).
    const history = (meta?.history ?? []).map((m) => ({ role: m.role, content: m.content }));
    const corpusId = corpusIdRef.current;
    const element = elementRef.current;

    let state = initialAgentTurnState();
    setTurn(state);
    setIsStreaming(true);
    const apply = (core: AgentStreamEvent | null) => {
      if (!core) return;
      state = applyAgentEvent(state, core);
      setTurn(state);
    };

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ message: text, session_id: sid, history, ...(corpusId ? { corpus_id: corpusId } : {}), ...(element ? { element } : {}) }),
        signal: controller.signal,
      });
      if (res.status === 401) {
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
          // DD-002C: do NOT latch the backend's per-turn session_id. The stable
          // client UUID (set in send()) is the conversation_store's key; with
          // history replay the backend runs session-less (backend_session_id=None),
          // so its result.session_id is irrelevant. Overwriting it here would make
          // turn B load an empty history → the model loses the thread.
          apply(mapEvent(ev));
        }
      }
    } catch (err) {
      // An abort is the framework's timeout watchdog cancelling us — it already
      // surfaced the timeout banner, so don't also emit a transport error.
      if (!(err instanceof DOMException && err.name === 'AbortError')) {
        apply({ type: 'error', message: err instanceof Error ? err.message : String(err) });
      }
    } finally {
      abortRef.current = null;
      setIsStreaming(false);
    }
  }, [isStreaming]);

  // Cancel the in-flight request (used by the framework's turn-timeout watchdog).
  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  // Reset ONLY the live turn. The session id is owned by the conversation
  // library now (a new/switched chat changes the id upstream), so reset() must
  // NOT touch it — nulling it here would break the active thread's continuity.
  // Used by the conversation layer's hydration and the auth banner's dismiss.
  const reset = useCallback(() => {
    setTurn(initialAgentTurnState());
  }, []);

  return { turn, isStreaming, send, reset, abort };
}
