/**
 * contracts/conversation-state.vectors.json — the thread around a turn, as a
 * contract: optimistic send, fold, failure with the draft handed back, retry,
 * hydration. The ops are abstract so the iPhone's harness can drive ChatModel
 * with the same file; here they become ConversationEvents.
 */

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import type { ChatMessage } from '../chat/message';
import type { MessageAuthor } from './events';
import { initialAgentTurnState } from './state';
import {
  applyConversationEvent,
  initialConversationState,
  type ConversationState,
} from './conversation-state';

interface Op {
  op: 'send' | 'settled' | 'failed' | 'retry' | 'hydrate' | 'dismiss_failure' | 'clear_unsent';
  text?: string;
  reactions?: string[];
  deferred?: boolean;
  message?: string;
  messages?: ChatMessage[];
}
interface Vector {
  name: string;
  ops: Op[];
  expect: unknown;
}

const here = dirname(fileURLToPath(import.meta.url));
const contrato = JSON.parse(
  readFileSync(resolve(here, '../../contracts/conversation-state.vectors.json'), 'utf8'),
) as { version: number; vectors: Vector[] };

const USUARIO: MessageAuthor = { id: 'user', name: 'Tú' };
const AGENTE: MessageAuthor = { id: 'og118', name: 'og118' };

function aplicar(state: ConversationState, op: Op): ConversationState {
  switch (op.op) {
    case 'send':
      return applyConversationEvent(state, { type: 'send', text: op.text ?? '', author: USUARIO, controlled: false });
    case 'retry': {
      const last = state.lastSent;
      if (!last) return state;
      return applyConversationEvent(state, { type: 'send', text: last.text, images: last.images, author: USUARIO, controlled: false });
    }
    case 'settled':
      return applyConversationEvent(state, {
        type: 'turn_settled',
        turn: {
          ...initialAgentTurnState(),
          text: op.text ?? '',
          reactions: op.reactions ?? [],
          deferred: op.deferred ?? false,
          status: 'done',
        },
        author: AGENTE,
        controlled: false,
      });
    case 'failed':
      return applyConversationEvent(state, { type: 'turn_failed', message: op.message, controlled: false });
    case 'hydrate':
      return applyConversationEvent(state, { type: 'hydrate', messages: op.messages ?? [] });
    case 'dismiss_failure':
      return applyConversationEvent(state, { type: 'dismiss_failure' });
    case 'clear_unsent':
      return applyConversationEvent(state, { type: 'clear_unsent' });
  }
}

function proyectar(s: ConversationState) {
  return {
    messages: s.messages.map((m) => ({ role: m.role, content: m.content })),
    failure: s.failure?.kind ?? null,
    unsentText: s.unsent.text,
    lastSentText: s.lastSent?.text ?? null,
  };
}

describe('conversation-state.vectors.json', () => {
  it('declara su versión y trae vectores', () => {
    expect(contrato.version).toBe(1);
    expect(contrato.vectors.length).toBeGreaterThan(0);
  });
  for (const v of contrato.vectors) {
    it(v.name, () => {
      const estado = v.ops.reduce(aplicar, initialConversationState());
      expect(proyectar(estado)).toEqual(v.expect);
    });
  }
});
