'use client';

/**
 * useFenixAgent — el TRANSPORTE de fenix (implementación de AgentHook de core).
 *
 * HALLAZGO-1 del experimento (ver .claude/EXPERIMENTO.md): `mapEvent` de abajo es
 * una copia CASI LITERAL de apps/og118/web/lib/useOg118Agent.ts. No contiene una
 * sola línea específica de og118 — es puro mapeo del contrato nativo de fi-runner
 * al union AgentStreamEvent de fi-core. Que el segundo consumer tenga que
 * copiarlo prueba que ese mapeo pertenece al framework (fi-glass o fi-core), no
 * al consumer. NO se movió porque la regla del experimento prohíbe tocar
 * fi-glass; queda anotado como evidencia.
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
import { AUTH401 } from './fenixToken';
import { fenixHeaders } from './fenixSesion';

const API = process.env.NEXT_PUBLIC_FENIX_API ?? 'http://localhost:8118';
const CORPUS = process.env.NEXT_PUBLIC_FENIX_CORPUS ?? '';

function mapEvent(ev: Record<string, unknown>): AgentStreamEvent | null {
  const data = (ev.data ?? {}) as Record<string, unknown>;
  switch (ev.type) {
    case 'open':
      return { type: 'open' };
    case 'text':
      return { type: 'text', delta: String(ev.text ?? '') };
    case 'element': {
      const el = (ev.element ?? {}) as Record<string, unknown>;
      const id = String(el.id ?? '');
      if (!id) return null;
      const label = String(el.label ?? '');
      return {
        type: 'author',
        author: {
          id,
          name: String(el.name ?? '') || label || id,
          symbol: (el.symbol as string | null) ?? null,
          engine: (el.engine as string | null) ?? null,
        },
      };
    }
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
      const model = typeof r.model === 'string' && r.model.trim() ? r.model : null;
      return {
        type: 'result',
        text: String(r.text ?? ''),
        ...(model ? { meta: { model } } : {}),
      };
    }
    case 'error':
      return { type: 'error', message: String(ev.message ?? 'error') };
    case 'ping':
      return { type: 'ping' };
    case 'done':
      return { type: 'done' };
    default:
      return null;
  }
}

export function useFenixAgent(sessionId: string | null, admin: boolean): AgentHook {
  const [turn, setTurn] = useState<AgentTurnState>(initialAgentTurnState());
  const [isStreaming, setIsStreaming] = useState(false);
  const sessionIdRef = useRef<string | null>(sessionId);
  sessionIdRef.current = sessionId;
  const abortRef = useRef<AbortController | null>(null);
  // El corpus del NEGOCIO sólo viaja desde el mostrador. Es una constante
  // NEXT_PUBLIC_, o sea horneada en el bundle y legible por cualquiera, y el
  // binding de fi-runner la convierte en "busca proactivamente en ese corpus":
  // mandarla desde una PC pública era servirle la lista maestra al modelo y
  // encima ordenarle usarla.
  const adminRef = useRef(admin);
  adminRef.current = admin;

  const send = useCallback(async (message: string, meta?: AgentSendMeta) => {
    const text = message.trim();
    const images = meta?.images && meta.images.length > 0 ? meta.images : undefined;
    if ((!text && !images) || isStreaming) return;
    const sid = sessionIdRef.current;
    if (!sid) return;

    const history = (meta?.history ?? []).map((m) => ({ role: m.role, content: m.content }));

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
        headers: { 'Content-Type': 'application/json', ...fenixHeaders() },
        body: JSON.stringify({
          message: text,
          session_id: sid,
          history,
          // fenix precarga SIEMPRE el corpus de la papelería: aquí no hay selector
          // de proyecto que el equipo pueda olvidar. Es la diferencia de producto
          // contra og118, no una limitación.
          ...(CORPUS && adminRef.current ? { corpus_id: CORPUS } : {}),
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
        const frames = buffer.split('\n\n');
        buffer = frames.pop() ?? '';
        for (const frame of frames) {
          const line = frame.split('\n').find((l) => l.startsWith('data:'));
          if (!line) continue;
          apply(mapEvent(JSON.parse(line.slice(5).trim())));
        }
      }
    } catch (err) {
      if (!(err instanceof DOMException && err.name === 'AbortError')) {
        apply({ type: 'error', message: err instanceof Error ? err.message : String(err) });
      }
    } finally {
      abortRef.current = null;
      setIsStreaming(false);
    }
  }, [isStreaming]);

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    setTurn(initialAgentTurnState());
  }, []);

  return { turn, isStreaming, send, reset, abort };
}
