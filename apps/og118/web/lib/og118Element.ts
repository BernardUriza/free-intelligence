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
