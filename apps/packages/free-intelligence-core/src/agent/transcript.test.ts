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

describe('makeUserMessage', () => {
  it('builds a user message with an ISO timestamp', () => {
    const msg = makeUserMessage('hola');
    expect(msg.role).toBe('user');
    expect(Number.isNaN(new Date(msg.timestamp).getTime())).toBe(false);
  });
});
