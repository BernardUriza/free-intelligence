/**
 * Unit tests for the conversation helpers (DD-002B1.1). These are pure,
 * deterministic functions; the tests pin the two things that matter most for a
 * substrate consumed by multiple apps: privacy-by-structure (sanitize drops
 * everything but role/content/timestamp) and deterministic derivation
 * (title/preview/record are reproducible given a fixed `now`).
 */

import { describe, it, expect } from 'vitest';
import type { ChatMessage } from '../chat/message';
import {
  CONVERSATION_SCHEMA_VERSION,
  createConversationRecord,
  summarizeConversation,
  organizeConversationSummaries,
  filterConversationSummaries,
  deriveConversationTitle,
  deriveConversationPreview,
  resolveConversationTitle,
  renameConversationRecord,
  setConversationPinned,
  setConversationArchived,
  sanitizeConversationMessage,
} from './helpers';

const NOW = '2026-06-09T00:00:00.000Z';

function msg(
  role: 'user' | 'assistant',
  content: string,
  extra: Partial<ChatMessage> = {},
): ChatMessage {
  return { role, content, timestamp: '2026-06-09T00:00:01.000Z', ...extra };
}

describe('sanitizeConversationMessage — privacy by structure', () => {
  it('keeps only role, content, timestamp', () => {
    const dirty: ChatMessage = {
      role: 'assistant',
      content: 'hola',
      timestamp: NOW,
      id: 'abc123',
      thinking: 'secret chain of thought',
      metadata: { token: 'Bearer xyz', tool: { payload: 'danger' } },
    };
    const clean = sanitizeConversationMessage(dirty);
    expect(clean).toEqual({ role: 'assistant', content: 'hola', timestamp: NOW });
    expect('id' in clean).toBe(false);
    expect('thinking' in clean).toBe(false);
    expect('metadata' in clean).toBe(false);
  });

  it('drops unknown future fields by construction', () => {
    const future = {
      role: 'user',
      content: 'x',
      timestamp: NOW,
      futureSecret: 'should not survive',
    } as unknown as ChatMessage;
    const clean = sanitizeConversationMessage(future);
    expect(Object.keys(clean).sort()).toEqual(['content', 'role', 'timestamp']);
  });

  it('preserves the glass-box trace (B3-FIGLASS-TRACE-PERSISTENCE-1)', () => {
    const traced: ChatMessage = {
      role: 'assistant',
      content: 'aquí tienes el plan',
      timestamp: NOW,
      trace: {
        plan: { steps: [{ label: 'Investigar', status: 'done' }], outcome: 'completed' },
        tools: [{ id: 't1', name: 'search_documents', server: 'rag', isError: false }],
        sources: ['doc://a'],
      },
    };
    const clean = sanitizeConversationMessage(traced);
    expect(clean.trace?.plan?.steps).toHaveLength(1);
    expect(clean.trace?.tools?.[0].name).toBe('search_documents');
    expect(clean.trace?.sources).toEqual(['doc://a']);
  });

  it('still drops metadata even when a trace is present (no secret leak via the new field)', () => {
    const mixed: ChatMessage = {
      role: 'assistant',
      content: 'hola',
      timestamp: NOW,
      metadata: { token: 'Bearer xyz' },
      trace: { sources: ['doc://safe'] },
    };
    const clean = sanitizeConversationMessage(mixed);
    expect('metadata' in clean).toBe(false);
    expect(clean.trace?.sources).toEqual(['doc://safe']);
  });

  it('preserves attached images with exactly mediaType + data (OG118-IMAGE-UPLOAD-1)', () => {
    const withImage = {
      role: 'user',
      content: 'mira',
      timestamp: NOW,
      images: [{ mediaType: 'image/png', data: 'aGk=', extra: 'dropped' }],
    } as unknown as ChatMessage;
    const clean = sanitizeConversationMessage(withImage);
    expect(clean.images).toEqual([{ mediaType: 'image/png', data: 'aGk=' }]);
  });

  it('omits the images field when absent or empty (text-only records unchanged)', () => {
    expect('images' in sanitizeConversationMessage(msg('user', 'hola'))).toBe(false);
    expect(
      'images' in sanitizeConversationMessage(msg('user', 'hola', { images: [] })),
    ).toBe(false);
  });
});

describe('deriveConversationTitle', () => {
  it('uses the first non-empty user message, skipping assistant + empty', () => {
    const title = deriveConversationTitle([
      msg('assistant', 'intro screen'),
      msg('user', '   '),
      msg('user', 'How do I deploy og118?'),
      msg('user', 'second question'),
    ]);
    expect(title).toBe('How do I deploy og118?');
  });

  it('falls back to "New chat" with no usable user message', () => {
    expect(deriveConversationTitle([])).toBe('New chat');
    expect(deriveConversationTitle([msg('assistant', 'only assistant')])).toBe(
      'New chat',
    );
  });

  it('truncates deterministically with an ellipsis', () => {
    const long = 'a'.repeat(100);
    const title = deriveConversationTitle([msg('user', long)], 10);
    expect(title).toBe(`${'a'.repeat(9)}…`);
    expect(title.length).toBe(10);
  });
});

describe('deriveConversationPreview', () => {
  it('uses the last non-empty message of any role', () => {
    const preview = deriveConversationPreview([
      msg('user', 'first'),
      msg('assistant', 'last real answer'),
      msg('assistant', '   '),
    ]);
    expect(preview).toBe('last real answer');
  });

  it('returns empty string when nothing has content', () => {
    expect(deriveConversationPreview([])).toBe('');
    expect(deriveConversationPreview([msg('user', '  ')])).toBe('');
  });
});

describe('createConversationRecord', () => {
  it('stamps a deterministic now and the schema version', () => {
    const rec = createConversationRecord({
      id: 'sess-1',
      messages: [msg('user', 'hello there')],
      now: NOW,
    });
    expect(rec.id).toBe('sess-1');
    expect(rec.createdAt).toBe(NOW);
    expect(rec.updatedAt).toBe(NOW);
    expect(rec.schemaVersion).toBe(CONVERSATION_SCHEMA_VERSION);
    expect(rec.title).toBe('hello there');
    expect(rec.preview).toBe('hello there');
  });

  it('sanitizes the seeded messages', () => {
    const rec = createConversationRecord({
      id: 'sess-2',
      messages: [msg('user', 'hi', { metadata: { token: 'Bearer secret' } })],
      now: NOW,
    });
    expect(rec.messages[0]).toEqual({
      role: 'user',
      content: 'hi',
      timestamp: '2026-06-09T00:00:01.000Z',
    });
  });

  it('defaults to an empty thread', () => {
    const rec = createConversationRecord({ id: 'sess-3', now: NOW });
    expect(rec.messages).toEqual([]);
    expect(rec.title).toBe('New chat');
    expect(rec.preview).toBe('');
  });
});

describe('summarizeConversation', () => {
  it('excludes the messages array', () => {
    const rec = createConversationRecord({
      id: 'sess-4',
      messages: [msg('user', 'q'), msg('assistant', 'a')],
      now: NOW,
    });
    const summary = summarizeConversation(rec);
    expect('messages' in summary).toBe(false);
    expect(summary).toEqual({
      id: 'sess-4',
      title: 'q',
      createdAt: NOW,
      updatedAt: NOW,
      preview: 'a',
    });
  });
});

const LATER = '2026-06-10T00:00:00.000Z';

describe('renameConversationRecord — user rename', () => {
  it('stores a non-empty title verbatim and marks it custom', () => {
    const rec = createConversationRecord({
      id: 'r1',
      messages: [msg('user', 'derived from this')],
      now: NOW,
    });
    const next = renameConversationRecord(rec, '  My  cool   chat  ', LATER);
    expect(next.title).toBe('My cool chat');
    expect(next.titleCustom).toBe(true);
    expect(next.updatedAt).toBe(LATER);
    expect(next.createdAt).toBe(NOW); // untouched
    expect(rec.titleCustom).toBeUndefined(); // pure: original not mutated
  });

  it('caps a custom title at the title max length', () => {
    const rec = createConversationRecord({ id: 'r2', now: NOW });
    const long = 'x'.repeat(200);
    const next = renameConversationRecord(rec, long, LATER);
    expect(next.title.length).toBe(60);
    expect(next.titleCustom).toBe(true);
  });

  it('reverts to the derived title and clears custom on an empty title', () => {
    const rec = renameConversationRecord(
      createConversationRecord({
        id: 'r3',
        messages: [msg('user', 'original question')],
        now: NOW,
      }),
      'renamed',
      LATER,
    );
    expect(rec.titleCustom).toBe(true);
    const reverted = renameConversationRecord(rec, '   ', LATER);
    expect(reverted.title).toBe('original question');
    expect(reverted.titleCustom).toBe(false);
  });
});

describe('resolveConversationTitle — persist preserves a rename', () => {
  it('derives from messages when there is no custom title', () => {
    const messages = [msg('user', 'fresh derive')];
    expect(resolveConversationTitle(messages)).toBe('fresh derive');
    expect(
      resolveConversationTitle(messages, { title: 'old', titleCustom: false }),
    ).toBe('fresh derive');
  });

  it('keeps a custom title instead of re-deriving', () => {
    const messages = [msg('user', 'would derive to this')];
    expect(
      resolveConversationTitle(messages, {
        title: 'User Named It',
        titleCustom: true,
      }),
    ).toBe('User Named It');
  });

  it('falls back to derive when a custom title is blank', () => {
    const messages = [msg('user', 'derive fallback')];
    expect(
      resolveConversationTitle(messages, { title: '   ', titleCustom: true }),
    ).toBe('derive fallback');
  });
});

describe('sanitizeConversationMessage — the author survives persistence', () => {
  it('keeps the author (a reloaded thread must still say who spoke)', () => {
    const clean = sanitizeConversationMessage(
      msg('assistant', 'hola', {
        author: { id: 'element-053-i-yodo', name: 'Yodo', symbol: 'I' },
        metadata: { token: 'Bearer xyz' },
      }),
    );
    expect(clean.author).toEqual({ id: 'element-053-i-yodo', name: 'Yodo', symbol: 'I' });
    expect('metadata' in clean).toBe(false);
  });

  it('omits author when the message has none', () => {
    expect('author' in sanitizeConversationMessage(msg('user', 'hola'))).toBe(false);
  });
});

describe('pin/archive transformers + organize (CONV-ORGANIZE-1)', () => {
  const LATER2 = '2026-07-13T00:00:00.000Z';
  const base = () =>
    createConversationRecord({ id: 'p1', messages: [msg('user', 'hola')], now: NOW });

  it('pin stamps pinnedAt without touching updatedAt; unpin drops the field', () => {
    const pinned = setConversationPinned(base(), true, LATER2);
    expect(pinned.pinnedAt).toBe(LATER2);
    expect(pinned.updatedAt).toBe(NOW);
    const unpinned = setConversationPinned(pinned, false, LATER2);
    expect('pinnedAt' in unpinned).toBe(false);
    expect(unpinned.updatedAt).toBe(NOW);
  });

  it('archive stamps archivedAt and clears the pin; unarchive drops the field', () => {
    const pinned = setConversationPinned(base(), true, LATER2);
    const archived = setConversationArchived(pinned, true, LATER2);
    expect(archived.archivedAt).toBe(LATER2);
    expect('pinnedAt' in archived).toBe(false);
    const restored = setConversationArchived(archived, false, LATER2);
    expect('archivedAt' in restored).toBe(false);
  });

  it('pinning an archived record lifts it out of the archive', () => {
    const archived = setConversationArchived(base(), true, LATER2);
    const pinned = setConversationPinned(archived, true, LATER2);
    expect('archivedAt' in pinned).toBe(false);
    expect(pinned.pinnedAt).toBe(LATER2);
  });

  it('summarizeConversation carries the flags only when present', () => {
    const plain = summarizeConversation(base());
    expect('pinnedAt' in plain).toBe(false);
    expect('archivedAt' in plain).toBe(false);
    const pinned = summarizeConversation(setConversationPinned(base(), true, LATER2));
    expect(pinned.pinnedAt).toBe(LATER2);
  });

  it('organizes into pinned (last-pinned first) / active (recent first) / archived', () => {
    const sum = (
      id: string,
      updatedAt: string,
      extra: { pinnedAt?: string; archivedAt?: string } = {},
    ) => ({ id, title: id, createdAt: NOW, updatedAt, preview: '', ...extra });
    const { pinned, active, archived } = organizeConversationSummaries([
      sum('active-old', '2026-07-01T00:00:00.000Z'),
      sum('pin-early', '2026-07-05T00:00:00.000Z', { pinnedAt: '2026-07-10T00:00:00.000Z' }),
      sum('archived-1', '2026-07-09T00:00:00.000Z', { archivedAt: '2026-07-11T00:00:00.000Z' }),
      sum('pin-late', '2026-07-02T00:00:00.000Z', { pinnedAt: '2026-07-12T00:00:00.000Z' }),
      sum('active-new', '2026-07-08T00:00:00.000Z'),
      sum('archived-2', '2026-07-03T00:00:00.000Z', { archivedAt: '2026-07-12T12:00:00.000Z' }),
    ]);
    expect(pinned.map((s) => s.id)).toEqual(['pin-late', 'pin-early']);
    expect(active.map((s) => s.id)).toEqual(['active-new', 'active-old']);
    expect(archived.map((s) => s.id)).toEqual(['archived-2', 'archived-1']);
  });
});

describe('filterConversationSummaries (CONV-SEARCH-1)', () => {
  const sum = (id: string, title: string, preview = '') => ({
    id, title, createdAt: NOW, updatedAt: NOW, preview,
  });
  const list = [
    sum('a', 'Sistemas distribuidos', 'la red no es confiable'),
    sum('b', 'Métodos de natación', 'entrenados en 25 metros'),
    sum('c', 'Plan de comidas', 'menú semanal vegano'),
  ];

  it('matches case- and diacritic-insensitively over title and preview', () => {
    expect(filterConversationSummaries(list, 'metodos').map((s) => s.id)).toEqual(['b']);
    expect(filterConversationSummaries(list, 'MENÚ').map((s) => s.id)).toEqual(['c']);
    expect(filterConversationSummaries(list, 'confiable').map((s) => s.id)).toEqual(['a']);
  });

  it('requires every term to match (AND semantics)', () => {
    expect(filterConversationSummaries(list, 'natacion metros').map((s) => s.id)).toEqual(['b']);
    expect(filterConversationSummaries(list, 'natacion vegano')).toEqual([]);
  });

  it('returns the input untouched for an empty or whitespace query', () => {
    expect(filterConversationSummaries(list, '')).toBe(list);
    expect(filterConversationSummaries(list, '   ')).toBe(list);
  });
});
