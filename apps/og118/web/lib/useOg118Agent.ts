'use client';

/**
 * useOg118Agent — og118's implementation of core's AgentHook (the TRANSPORT).
 *
 * Reads the SSE frames and hands each one to core's `fromWireEvent`, then feeds
 * the pure `applyAgentEvent` reducer (Berkelio) to build the live AgentTurnState.
 * This hook owns ONE live turn — the conversation transcript is NOT here. The
 * visible thread (user message, assistant fold, transcript) is the framework's
 * job: fi-glass `useAgentConversation` wraps this hook (DD-002-LESSON — the
 * reusable primitive lives in the framework, not the consumer).
 *
 * Mapping surface (fi-runner → core), documented in VALIDATION_REPORT:
 *   {type:'text', text}                  → {type:'text', delta}
 *   {type:'element', element:{id,label,name,symbol,engine}} → {type:'author', author}
 *   {type:'tool_call', tool:{id,name,server,is_error}} → {type:'tool_call', call:{id,name,server,isError}}
 *   {type:'plan', data:{steps}}          → {type:'plan', steps}
 *   {type:'step_started', data:{step_index}} → {type:'step_started', index}
 *   {type:'step_done', data:{step_index,status,summary?,error?}} → {type:'step_done', index, status, ...}
 *   {type:'result', result:{text,model,…}} → {type:'result', text, meta:{model}}
 *   open / ping / done                   → pass-through
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
  fromWireEvent,
  takeSseFrames,
} from '@free-intelligence/core';
import { authHeaders, AUTH401 } from './og118Token';
import { proyectosActivos } from './og118Flags';

const API = process.env.NEXT_PUBLIC_OG118_API ?? 'http://localhost:8118';

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
    // OG118-IMAGE-UPLOAD-1: an image-only send (empty text, ≥1 image) is valid —
    // the picture IS the message. A truly empty send stays a no-op.
    const images = meta?.images && meta.images.length > 0 ? meta.images : undefined;
    if ((!text && !images) || isStreaming) return;
    const sid = sessionIdRef.current;
    if (!sid) return; // no active conversation yet — controlled no-op

    // og118 is local-first: the durable transcript lives in the browser (IndexedDB
    // via useConversationLibrary). We replay the confirmed thread on each turn so
    // continuity survives a recycled/redeployed backend with NO server-side store.
    // Send ONLY role/content — never ids, timestamps, tool payloads, audio
    // metadata, or prior images (privacy + the backend treats it as untrusted
    // context, not auth; the history fold is text-only, so a re-shown image is
    // re-attached by the user, never silently re-uploaded).
    const history = (meta?.history ?? []).map((m) => ({ role: m.role, content: m.content }));
    // With Projects hidden there is no corpus to bind: the key is omitted from
    // the wire entirely. The server still ACCEPTS `corpus_id` with its own flag
    // off (it ignores it, so an old open tab keeps chatting) — but sending a key
    // the backend has decided to ignore is a lie in the payload, so we drop it.
    const corpusId = proyectosActivos() ? corpusIdRef.current : null;
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
        body: JSON.stringify({
          message: text,
          session_id: sid,
          history,
          ...(corpusId ? { corpus_id: corpusId } : {}),
          ...(element ? { element } : {}),
          // Current-turn vision input, in the server's ChatImage shape.
          ...(images ? { images: images.map((i) => ({ media_type: i.mediaType, data: i.data })) } : {}),
        }),
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
        const corte = takeSseFrames(buffer);
        buffer = corte.rest;
        for (const payload of corte.payloads) {
          const ev = JSON.parse(payload);
          // DD-002C: do NOT latch the backend's per-turn session_id. The stable
          // client UUID (set in send()) is the conversation_store's key; with
          // history replay the backend runs session-less (backend_session_id=None),
          // so its result.session_id is irrelevant. Overwriting it here would make
          // turn B load an empty history → the model loses the thread.
          apply(fromWireEvent(ev));
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
    abortRef.current?.abort();
    setTurn(initialAgentTurnState());
  }, []);

  return { turn, isStreaming, send, reset, abort };
}
