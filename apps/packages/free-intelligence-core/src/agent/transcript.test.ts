/**
 * Tests for the transcript bridge — that provenance survives the fold: model
 * (turn.meta.model → metadata.model), the glass-box trace, and WHO SPOKE
 * (turn.author / the agent's default → message.author), so a shell's transcript
 * can attribute every bubble instead of hardcoding the app's own name.
 */

import { describe, it, expect } from 'vitest';
import { foldAssistantTurn, makeUserMessage } from './transcript';
import { initialAgentTurnState } from './state';
import type { AgentTurnState } from './state';
import type { MessageAuthor } from './events';

const OG118: MessageAuthor = { id: 'og118', name: 'og118', symbol: 'og' };
const YODO: MessageAuthor = {
  id: 'element-053-i-yodo',
  name: 'Yodo',
  symbol: 'I',
  engine: 'Insult',
};
const USER: MessageAuthor = { id: 'user', name: 'Tú' };

function turnWith(partial: Partial<AgentTurnState>): AgentTurnState {
  return { ...initialAgentTurnState(), text: 'hola', ...partial };
}

describe('foldAssistantTurn — authorship (no text without an author)', () => {
  it('attributes the turn to the speaker the backend announced', () => {
    const msg = foldAssistantTurn(turnWith({ author: YODO }), OG118);
    expect(msg.author).toEqual(YODO);
  });

  it('falls back to the agent identity when the backend named no speaker', () => {
    const msg = foldAssistantTurn(turnWith({ author: null }), OG118);
    expect(msg.author).toEqual(OG118);
  });

  it('never folds an assistant message without an author', () => {
    expect(foldAssistantTurn(turnWith({}), OG118).author).toBeDefined();
  });

  it('the announced speaker WINS over the app default (the og118 bug)', () => {
    // The regression this contract exists for: og118 rendered "og118" on every
    // bubble, so an answer produced by the Yodo element was attributed to the app.
    const msg = foldAssistantTurn(turnWith({ author: YODO }), OG118);
    expect(msg.author?.name).toBe('Yodo');
    expect(msg.author?.name).not.toBe('og118');
  });
});

describe('foldAssistantTurn — model provenance', () => {
  it('persists turn.meta.model into metadata.model', () => {
    const msg = foldAssistantTurn(turnWith({ meta: { model: 'gpt-5.2-mini' } }), OG118);
    expect(msg.role).toBe('assistant');
    expect(msg.metadata).toEqual({ model: 'gpt-5.2-mini' });
  });

  it('omits metadata entirely when the turn has no model', () => {
    expect(foldAssistantTurn(turnWith({ meta: null }), OG118).metadata).toBeUndefined();
    expect(
      foldAssistantTurn(turnWith({ meta: { latencyMs: 12 } }), OG118).metadata,
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
      OG118,
    );
    expect(msg.trace?.plan?.steps).toHaveLength(2);
    expect(msg.trace?.plan?.outcome).toBe('completed');
    expect(msg.trace?.tools).toEqual([
      { id: 't1', name: 'search_documents', server: 'rag', isError: false },
    ]);
    expect(msg.trace?.sources).toEqual(['doc://a', 'doc://b']);
  });

  it('omits trace entirely for a plain conversational turn (no plan/tools/sources)', () => {
    const msg = foldAssistantTurn(turnWith({ text: '¡Hola! ¿En qué te ayudo?' }), OG118);
    expect(msg.trace).toBeUndefined();
    expect(msg.content).toBe('¡Hola! ¿En qué te ayudo?');
  });

  it('includes only the non-empty parts of the trace', () => {
    const onlyTools = foldAssistantTurn(
      turnWith({ steps: [{ id: 'x', name: 'fetch', server: null, isError: null }] }),
      OG118,
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
      OG118,
    );
    expect(msg.trace?.plan?.steps).toHaveLength(1);
  });

  it('treats an empty plan (zero steps) as no plan', () => {
    const msg = foldAssistantTurn(turnWith({ plan: { steps: [] } }), OG118);
    expect(msg.trace).toBeUndefined();
  });
});

describe('makeUserMessage', () => {
  it('builds an authored user message with an ISO timestamp', () => {
    const msg = makeUserMessage('hola', USER);
    expect(msg.role).toBe('user');
    expect(msg.author).toEqual(USER);
    expect(Number.isNaN(new Date(msg.timestamp).getTime())).toBe(false);
  });

  it('attaches images when given (OG118-IMAGE-UPLOAD-1)', () => {
    const images = [{ mediaType: 'image/jpeg', data: 'aGk=' }];
    const msg = makeUserMessage('mira esto', USER, images);
    expect(msg.images).toEqual(images);
  });

  it('omits the images field for empty/absent lists (text-only shape unchanged)', () => {
    expect('images' in makeUserMessage('hola', USER)).toBe(false);
    expect('images' in makeUserMessage('hola', USER, [])).toBe(false);
  });
});
