/**
 * contracts/conversation-derivations.vectors.json — title, preview, rename and
 * the sidebar's three sections, as a contract both the web and the iPhone obey.
 * The JSON is the source; a red vector here is core drifting from it.
 */

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import type { ChatMessage } from '../chat/message';
import type { ConversationRecord, ConversationSummary } from './record';
import {
  conversationRenamePatch,
  deriveConversationPreview,
  deriveConversationTitle,
  organizeConversationSummaries,
} from './helpers';

interface Vector {
  name: string;
  kind: 'title' | 'preview' | 'rename' | 'organize';
  input: Record<string, unknown>;
  expect: unknown;
}

const here = dirname(fileURLToPath(import.meta.url));
const contrato = JSON.parse(
  readFileSync(resolve(here, '../../contracts/conversation-derivations.vectors.json'), 'utf8'),
) as { version: number; vectors: Vector[] };

function correr(v: Vector): unknown {
  switch (v.kind) {
    case 'title':
      return deriveConversationTitle(v.input.messages as ChatMessage[]);
    case 'preview':
      return deriveConversationPreview(v.input.messages as ChatMessage[]);
    case 'rename': {
      const base = v.input.record as Pick<ConversationRecord, 'title' | 'titleCustom' | 'messages'>;
      const record = { ...base, id: 'c', createdAt: '', updatedAt: '', preview: '', schemaVersion: 1 };
      const patch = conversationRenamePatch(record, v.input.newTitle as string, '2026-10-17T00:00:00Z');
      return { title: patch.title, titleCustom: patch.titleCustom === true };
    }
    case 'organize': {
      const o = organizeConversationSummaries(v.input.summaries as ConversationSummary[]);
      return {
        pinned: o.pinned.map((s) => s.id),
        active: o.active.map((s) => s.id),
        archived: o.archived.map((s) => s.id),
      };
    }
  }
}

describe('conversation-derivations.vectors.json', () => {
  it('declara su versión y trae vectores', () => {
    expect(contrato.version).toBe(1);
    expect(contrato.vectors.length).toBeGreaterThan(0);
  });
  for (const v of contrato.vectors) {
    it(v.name, () => {
      expect(correr(v)).toEqual(v.expect);
    });
  }
});
