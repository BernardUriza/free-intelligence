/**
 * Tests for the transcript bridge — specifically that model provenance
 * survives the fold (turn.meta.model → message.metadata.model) so a shell's
 * badge slot has real data after persistence.
 */

import { describe, it, expect } from 'vitest';
import { foldAssistantTurn, makeUserMessage } from './transcript';
import { initialAgentTurnState } from './state';
import type { AgentTurnState } from './state';

function turnWith(partial: Partial<AgentTurnState>): AgentTurnState {
  return { ...initialAgentTurnState(), text: 'hola', ...partial };
}

describe('foldAssistantTurn — model provenance', () => {
  it('persists turn.meta.model into metadata.model', () => {
    const msg = foldAssistantTurn(
      turnWith({ meta: { model: 'gpt-5.2-mini' } }),
    );
    expect(msg.role).toBe('assistant');
    expect(msg.metadata).toEqual({ model: 'gpt-5.2-mini' });
  });

  it('omits metadata entirely when the turn has no model', () => {
    expect(foldAssistantTurn(turnWith({ meta: null })).metadata).toBeUndefined();
    expect(
      foldAssistantTurn(turnWith({ meta: { latencyMs: 12 } })).metadata,
    ).toBeUndefined();
  });
});

describe('foldAssistantTurn — glass-box trace (B3-FIGLASS-TRACE-PERSISTENCE-1)', () => {
  it('snapshots the declared plan, tools and sources into trace', () => {
    const msg = foldAssistantTurn(
      turnWith({
        plan: {
          steps: [
            { label: 'Investigar', status: 'done', summary: 'listo' },
            { label: 'Responder', status: 'done' },
          ],
          outcome: 'completed',
        },
        steps: [{ id: 't1', name: 'search_documents', server: 'rag', isError: false }],
        sources: ['doc://a', 'doc://b'],
      }),
    );
    expect(msg.trace?.plan?.steps).toHaveLength(2);
    expect(msg.trace?.plan?.outcome).toBe('completed');
    expect(msg.trace?.tools).toEqual([
      { id: 't1', name: 'search_documents', server: 'rag', isError: false },
    ]);
    expect(msg.trace?.sources).toEqual(['doc://a', 'doc://b']);
  });

  it('omits trace entirely for a plain conversational turn (no plan/tools/sources)', () => {
    const msg = foldAssistantTurn(turnWith({ text: '¡Hola! ¿En qué te ayudo?' }));
    expect(msg.trace).toBeUndefined();
    expect(msg.content).toBe('¡Hola! ¿En qué te ayudo?');
  });

  it('includes only the non-empty parts of the trace', () => {
    const onlyTools = foldAssistantTurn(
      turnWith({ steps: [{ id: 'x', name: 'fetch', server: null, isError: null }] }),
    );
    expect(onlyTools.trace).toEqual({
      tools: [{ id: 'x', name: 'fetch', server: null, isError: null }],
    });
    expect(onlyTools.trace?.plan).toBeUndefined();
    expect(onlyTools.trace?.sources).toBeUndefined();
  });

  it('keeps a declared plan with zero settled steps (planning itself is the signal)', () => {
    const msg = foldAssistantTurn(
      turnWith({ plan: { steps: [{ label: 'Paso 1', status: 'pending' }] } }),
    );
    expect(msg.trace?.plan?.steps).toHaveLength(1);
  });

  it('treats an empty plan (zero steps) as no plan', () => {
    const msg = foldAssistantTurn(turnWith({ plan: { steps: [] } }));
    expect(msg.trace).toBeUndefined();
  });
});

describe('makeUserMessage', () => {
  it('builds a user message with an ISO timestamp', () => {
    const msg = makeUserMessage('hola');
    expect(msg.role).toBe('user');
    expect(Number.isNaN(new Date(msg.timestamp).getTime())).toBe(false);
  });
});
