/**
 * The conversation machine, exercised WITHOUT React.
 *
 * Every rule below used to require mounting a hook and driving a fake transport
 * to observe. They are not React rules — they are conversation rules, and this
 * file is the evidence that moving them into core made them directly testable.
 */

import { describe, it, expect } from 'vitest';
import {
  initialConversationState,
  applyConversationEvent,
  type ConversationState,
} from './conversation-state';
import { initialAgentTurnState } from './state';
import type { AgentTurnState } from './state';

const AGENT = { id: 'og118', label: 'og118' } as const;
const USER = { id: 'user', label: 'Tú' } as const;

const send = (s: ConversationState, text: string, images?: { mediaType: string; data: string }[]) =>
  applyConversationEvent(s, { type: 'send', text, images, author: USER, controlled: false });

const settledTurn = (text: string): AgentTurnState => ({
  ...initialAgentTurnState(),
  text,
  status: 'done',
});

describe('the optimistic push', () => {
  it('adds the user message and marks the change un-persistable', () => {
    const s = send(initialConversationState(), 'hola');
    expect(s.messages).toHaveLength(1);
    expect(s.messages[0].role).toBe('user');
    expect(s.pending).toBe(true);
    // An optimistic push is NOT a confirmed turn; persisting it would leave a
    // durable lone user message if the turn then failed.
    expect(s.skipPersist).toBe(true);
  });

  it('a controlled shell gets no optimistic push (its consumer owns the thread)', () => {
    const s = applyConversationEvent(initialConversationState(), {
      type: 'send',
      text: 'hola',
      author: USER,
      controlled: true,
    });
    expect(s.messages).toHaveLength(0);
    expect(s.pending).toBe(true);
  });

  it('an image-only send is valid — the picture IS the message', () => {
    const s = send(initialConversationState(), '', [{ mediaType: 'image/png', data: 'AAA' }]);
    expect(s.messages).toHaveLength(1);
    expect(s.lastSent?.images).toHaveLength(1);
  });

  it('a truly empty send is a no-op', () => {
    const before = initialConversationState();
    expect(send(before, '   ')).toBe(before);
  });
});

describe('a failed turn must never cost the user their words', () => {
  it('hands back the TEXT on a transport failure', () => {
    let s = send(initialConversationState(), 'un prompt que me costó escribir');
    s = applyConversationEvent(s, { type: 'turn_failed', controlled: false });
    expect(s.messages).toHaveLength(0);
    expect(s.unsent.text).toBe('un prompt que me costó escribir');
    expect(s.failure?.kind).toBe('stream');
  });

  it('hands back the IMAGES too — the composer already cleared its drafts', () => {
    const img = { mediaType: 'image/png', data: 'BASE64' };
    let s = send(initialConversationState(), 'mira esto', [img]);
    s = applyConversationEvent(s, { type: 'turn_timeout', controlled: false });
    expect(s.unsent.text).toBe('mira esto');
    expect(s.unsent.images).toEqual([img]);
  });

  it('reverts on a timeout and refuses to re-arm afterwards', () => {
    let s = send(initialConversationState(), 'hola');
    s = applyConversationEvent(s, { type: 'turn_timeout', controlled: false });
    expect(s.timedOut).toBe(true);
    expect(s.failure?.kind).toBe('timeout');
    const again = applyConversationEvent(s, { type: 'turn_timeout', controlled: false });
    expect(again).toBe(s);
  });

  it('an app-handled error still REVERTS, it only suppresses the generic banner', () => {
    let s = send(initialConversationState(), 'hola');
    s = applyConversationEvent(s, { type: 'turn_failed', controlled: false, appHandled: true });
    // The words come back either way — the app owning the banner must not cost
    // the user their prompt.
    expect(s.unsent.text).toBe('hola');
    expect(s.failure).toBeNull();
  });

  it('a new send supersedes a draft still waiting to be recovered', () => {
    let s = send(initialConversationState(), 'primero');
    s = applyConversationEvent(s, { type: 'turn_failed', controlled: false });
    expect(s.unsent.text).toBe('primero');
    s = send(s, 'segundo');
    expect(s.unsent).toEqual({ text: null, images: null });
  });

  it('clear_unsent drops BOTH channels (a half-clear re-attaches a ghost)', () => {
    let s = send(initialConversationState(), 'con foto', [{ mediaType: 'image/png', data: 'A' }]);
    s = applyConversationEvent(s, { type: 'turn_failed', controlled: false });
    s = applyConversationEvent(s, { type: 'clear_unsent' });
    expect(s.unsent).toEqual({ text: null, images: null });
  });

  it('retry can replay the whole message, images included', () => {
    const img = { mediaType: 'image/png', data: 'A' };
    let s = send(initialConversationState(), 'con foto', [img]);
    s = applyConversationEvent(s, { type: 'turn_failed', controlled: false });
    expect(s.lastSent).toEqual({ text: 'con foto', images: [img] });
  });
});

describe('the fold', () => {
  it('folds the assistant turn and marks the change persistable', () => {
    let s = send(initialConversationState(), 'hola');
    s = applyConversationEvent(s, {
      type: 'turn_settled',
      turn: settledTurn('qué tal'),
      author: AGENT,
      controlled: false,
    });
    expect(s.messages).toHaveLength(2);
    expect(s.messages[1].role).toBe('assistant');
    expect(s.pending).toBe(false);
    // A settled turn IS confirmed — user + assistant persist together.
    expect(s.skipPersist).toBe(false);
  });

  it('a controlled shell never folds', () => {
    let s = applyConversationEvent(initialConversationState(), {
      type: 'send',
      text: 'hola',
      author: USER,
      controlled: true,
    });
    s = applyConversationEvent(s, {
      type: 'turn_settled',
      turn: settledTurn('qué tal'),
      author: AGENT,
      controlled: true,
    });
    expect(s.messages).toHaveLength(0);
  });

  it('a settle with no pending turn changes nothing', () => {
    const s = initialConversationState();
    expect(
      applyConversationEvent(s, {
        type: 'turn_settled',
        turn: settledTurn('x'),
        author: AGENT,
        controlled: false,
      }),
    ).toBe(s);
  });

  it('an empty-text settle closes the turn without folding a blank message', () => {
    let s = send(initialConversationState(), 'hola');
    s = applyConversationEvent(s, {
      type: 'turn_settled',
      turn: settledTurn(''),
      author: AGENT,
      controlled: false,
    });
    expect(s.messages).toHaveLength(1);
    expect(s.pending).toBe(false);
  });
});

describe('hydrate + immutability', () => {
  it('switching conversations drops the failure and the pending turn', () => {
    let s = send(initialConversationState(), 'hola');
    s = applyConversationEvent(s, { type: 'turn_failed', controlled: false });
    s = applyConversationEvent(s, { type: 'hydrate', messages: [] });
    expect(s.failure).toBeNull();
    expect(s.pending).toBe(false);
    expect(s.unsent).toEqual({ text: null, images: null });
    expect(s.skipPersist).toBe(true);
  });

  it('never mutates the state it is given', () => {
    const before = initialConversationState();
    const snapshot = JSON.stringify(before);
    send(before, 'hola');
    expect(JSON.stringify(before)).toBe(snapshot);
  });
});
