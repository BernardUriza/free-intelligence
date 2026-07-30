import { describe, expect, it } from 'vitest';
import type { ConversationRecord } from '@free-intelligence/core';
import { EphemeralConversationLibrary } from './EphemeralConversationLibrary';

function record(id: string, updatedAt: string, title = id): ConversationRecord {
  return {
    id,
    title,
    createdAt: '2026-01-01T00:00:00.000Z',
    updatedAt,
    preview: '',
    schemaVersion: 1,
    messages: [{ id: `${id}-m1`, role: 'user', content: 'hola', createdAt: updatedAt }],
  } as unknown as ConversationRecord;
}

describe('EphemeralConversationLibrary', () => {
  it('stores and returns a record', async () => {
    const lib = new EphemeralConversationLibrary();
    await lib.put(record('a', '2026-01-02T00:00:00.000Z'));

    expect(await lib.get('a')).toMatchObject({ id: 'a', title: 'a' });
    expect(await lib.get('missing')).toBeNull();
  });

  it('lists summaries newest first, without the message bodies', async () => {
    const lib = new EphemeralConversationLibrary();
    await lib.put(record('old', '2026-01-01T00:00:00.000Z'));
    await lib.put(record('new', '2026-03-01T00:00:00.000Z'));

    const list = await lib.list();
    expect(list.map((c) => c.id)).toEqual(['new', 'old']);
    expect(list[0]).not.toHaveProperty('messages');
  });

  it('upserts by id instead of duplicating', async () => {
    const lib = new EphemeralConversationLibrary();
    await lib.put(record('a', '2026-01-01T00:00:00.000Z', 'primero'));
    await lib.put(record('a', '2026-01-02T00:00:00.000Z', 'corregido'));

    expect(await lib.list()).toHaveLength(1);
    expect((await lib.get('a'))?.title).toBe('corregido');
  });

  it('hands out copies, so a caller mutating what it read cannot reach the store', async () => {
    const lib = new EphemeralConversationLibrary();
    await lib.put(record('a', '2026-01-01T00:00:00.000Z'));

    const leido = await lib.get('a');
    leido!.messages.push({
      id: 'intruso',
      role: 'user',
      content: 'no debería quedar',
      createdAt: '2026-01-01T00:00:00.000Z',
    } as never);

    expect((await lib.get('a'))?.messages).toHaveLength(1);
  });

  it('deletes one and clears all', async () => {
    const lib = new EphemeralConversationLibrary();
    await lib.put(record('a', '2026-01-01T00:00:00.000Z'));
    await lib.put(record('b', '2026-01-02T00:00:00.000Z'));

    await lib.delete('a');
    expect(await lib.get('a')).toBeNull();
    expect(await lib.list()).toHaveLength(1);

    await lib.delete('a');
    await lib.clear();
    expect(await lib.list()).toEqual([]);
  });

  // Lo que hace efímera a la librería: dos instancias no comparten nada. En el
  // cibercafé, cada pestaña es una sesión distinta y no debe heredar la anterior.
  it('shares nothing between instances', async () => {
    const primera = new EphemeralConversationLibrary();
    await primera.put(record('a', '2026-01-01T00:00:00.000Z'));

    expect(await new EphemeralConversationLibrary().list()).toEqual([]);
  });
});
