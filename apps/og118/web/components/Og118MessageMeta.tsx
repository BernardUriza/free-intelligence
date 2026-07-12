'use client';

/**
 * og118's own identity — WHO answers when no element is selected.
 *
 * This file used to hold two pieces of consumer wiring that both turned out to
 * sit at the wrong layer: a `renderHeader` that hardcoded the string "og118" (so
 * a selected element's answer was misattributed to the app), and a "powered by
 * <model>" chip fed from `message.metadata.model` — a field NOTHING ever wrote,
 * so it never rendered once. Both are the framework's job now, read off the
 * message's own `author` and `trace`. What legitimately belongs to the consumer
 * is what remains here: its name.
 */

import type { MessageAuthor } from '@free-intelligence/core';

/** og118 itself — the speaker when no element is selected (base companion). */
export const OG118_AUTHOR: MessageAuthor = { id: 'og118', name: 'og118', symbol: 'og' };
