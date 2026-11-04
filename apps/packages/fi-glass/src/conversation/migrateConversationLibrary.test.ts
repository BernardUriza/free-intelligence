import { describe, expect, it } from 'vitest';
import type { ChatMessage, ConversationRecord } from '@free-intelligence/core';
import { EphemeralConversationLibrary } from './EphemeralConversationLibrary';
import { migrateConversationLibrary } from './migrateConversationLibrary';

const T0 = '2026-10-09T10:00:00.000Z';
const T1 = '2026-10-09T10:01:00.000Z';
const T2 = '2026-10-09T10:02:00.000Z';
const T3 = '2026-10-09T10:03:00.000Z';

function msg(role: ChatMessage['role'], content: string, timestamp: string): ChatMessage {
  return { role, content, timestamp };
}

function rec(id: string, updatedAt: string, messages: ChatMessage[], extra: Partial<ConversationRecord> = {}): ConversationRecord {
  return {
    id,
    title: id,
    createdAt: T0,
    updatedAt,
    messages,
    preview: messages[messages.length - 1]?.content ?? '',
    schemaVersion: 1,
    ...extra,
  };
}

describe('migrateConversationLibrary', () => {
  it('copies a record the target does not have', async () => {
    const source = new EphemeralConversationLibrary();
    const target = new EphemeralConversationLibrary();
    await source.put(rec('A', T0, [msg('user', 'a', T0)]));
    const result = await migrateConversationLibrary(source, target);
    expect(result.migrated).toBe(1);
    expect((await target.get('A'))?.messages).toHaveLength(1);
  });

  it('merges a turn written locally into a conversation the cloud already has', async () => {
    const source = new EphemeralConversationLibrary();
    const target = new EphemeralConversationLibrary();
    const before = [msg('user', 'hola', T0), msg('assistant', 'qué tal', T1)];
    await target.put(rec('C', T1, before, { title: 'Mi título', titleCustom: true }));
    await source.put(
      rec('C', T3, [...before, msg('user', 'escrito offline', T2), msg('assistant', 'respuesta', T3)]),
    );

    const result = await migrateConversationLibrary(source, target);

    const merged = await target.get('C');
    expect(merged?.messages.map((m) => m.content)).toEqual([
      'hola',
      'qué tal',
      'escrito offline',
      'respuesta',
    ]);
    expect(merged?.title).toBe('Mi título');
    expect(merged?.preview).toBe('respuesta');
    expect(merged?.updatedAt).toBe(T3);
    expect(result.merged).toBe(1);
  });

  it('keeps cloud-only messages and orders the union by timestamp', async () => {
    const source = new EphemeralConversationLibrary();
    const target = new EphemeralConversationLibrary();
    await target.put(rec('C', T1, [msg('user', 'hola', T0), msg('user', 'desde el teléfono', T2)]));
    await source.put(rec('C', T3, [msg('user', 'hola', T0), msg('user', 'desde la laptop', T1)]));

    await migrateConversationLibrary(source, target);

    expect((await target.get('C'))?.messages.map((m) => m.content)).toEqual([
      'hola',
      'desde la laptop',
      'desde el teléfono',
    ]);
  });

  it('is idempotent: a second run writes nothing', async () => {
    const source = new EphemeralConversationLibrary();
    const target = new EphemeralConversationLibrary();
    await target.put(rec('C', T1, [msg('user', 'hola', T0)]));
    await source.put(rec('C', T3, [msg('user', 'hola', T0), msg('user', 'nuevo', T2)]));
    await migrateConversationLibrary(source, target);
    const second = await migrateConversationLibrary(source, target);
    expect(second).toEqual({ migrated: 0, merged: 0, skipped: 1 });
  });
});
