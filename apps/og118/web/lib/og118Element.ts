'use client';

/**
 * og118 "elemento" selection — the active persona slot for the chat (the picker
 * that makes og118 a ChatGPT replacement: switching elements = switching custom
 * GPTs). The chosen element's SLUG is the token sent in the chat request's
 * `element` field; the backend registry resolves it (slug/symbol/atomic/alias).
 *
 * Selection persists in localStorage, scoped by the signed-in identity via
 * `scopedStoreName` — two accounts on one browser never inherit each other's
 * active element (same boundary as conversations/audio/projects). An empty slug
 * ('') means the BASE og118 companion: no `element` is sent, base persona answers.
 */

import { scopedStoreName } from 'fi-glass/identity';

const BASE_KEY = 'og118-selected-element';

/** The base companion option — selecting it sends no element (base persona). */
export const BASE_ELEMENT_SLUG = '';

export interface Og118Element {
  id: string;
  atomicNumber: number;
  symbol: string;
  slug: string;
  displayName: string;
  displayLabel: string;
  status: string;
  aliases: string[];
  description?: string | null;
  engine?: string | null;
}

export function getSelectedElement(userId: string | null): string {
  if (typeof window === 'undefined') return BASE_ELEMENT_SLUG;
  try {
    return window.localStorage.getItem(scopedStoreName(BASE_KEY, userId)) ?? BASE_ELEMENT_SLUG;
  } catch {
    return BASE_ELEMENT_SLUG;
  }
}

export function setSelectedElement(userId: string | null, slug: string): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(scopedStoreName(BASE_KEY, userId), slug);
  } catch {
    /* private mode / storage disabled — selection just won't persist */
  }
}

/** An empty slot a new element can claim (GET /elements/slots). */
export interface Og118EmptySlot {
  atomicNumber: number;
  symbol: string;
  slug: string;
  displayName: string;
}

/** The engines a new element can ride; Codex pins GPT-6 Astra through AIRE. */
export const ELEMENT_ENGINES = [
  { id: 'claude', label: 'Claude (ruteo por turno)', provider: 'claude', model: null },
  { id: 'codex', label: 'GPT-6 Astra (Codex)', provider: 'codex', model: 'gpt-6-astra' },
] as const;

export type ElementEngineId = (typeof ELEMENT_ENGINES)[number]['id'];

/** A persona id the engine accepts: the slot's slug, lowercased, `[a-z0-9_]{1,32}`. */
export function personaIdFor(slug: string): string {
  return slug
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, '_')
    .slice(0, 32);
}
