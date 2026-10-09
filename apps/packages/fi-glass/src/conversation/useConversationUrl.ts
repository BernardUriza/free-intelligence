'use client';

import { useEffect, useRef } from 'react';
import type { ConversationSummary } from '@free-intelligence/core';

export const DEFAULT_CONVERSATION_PATH_PREFIX = '/c/';

/** The conversation id a path names (`/c/<id>` or `/c/<id>/`), or `null` for any other path. */
export function readConversationIdFromPath(
  pathname: string,
  prefix: string = DEFAULT_CONVERSATION_PATH_PREFIX,
): string | null {
  if (!pathname.startsWith(prefix)) return null;
  const id = decodeURIComponent(pathname.slice(prefix.length).replace(/\/+$/, ''));
  return id && !id.includes('/') ? id : null;
}

/** The id the current address names — call it once, before the library mounts. */
export function readConversationIdFromLocation(
  prefix: string = DEFAULT_CONVERSATION_PATH_PREFIX,
): string | null {
  if (typeof window === 'undefined') return null;
  return readConversationIdFromPath(window.location.pathname, prefix);
}

export interface UseConversationUrlOptions {
  activeId: string | null;
  /** The library's summaries: an id becomes addressable once it is saved. */
  conversations: ConversationSummary[];
  /** Back/forward landed on another address: open that conversation, or a fresh one for `null`. */
  onNavigate: (conversationId: string | null) => void;
  /** Path prefix for a conversation. Default `/c/`. */
  prefix?: string;
  /** The address of "no conversation yet". Default `/`. */
  rootPath?: string;
}

// The address bar follows the open chat: saved at `/c/<id>`, fresh at `/`. Switching
// pushes history, a first save replaces `/` (same chat), back/forward reopen.
export function useConversationUrl({
  activeId,
  conversations,
  onNavigate,
  prefix = DEFAULT_CONVERSATION_PATH_PREFIX,
  rootPath = '/',
}: UseConversationUrlOptions): void {
  const onNavigateRef = useRef(onNavigate);
  onNavigateRef.current = onNavigate;
  const shownId = useRef<string | null | undefined>(undefined);

  const saved = activeId !== null && conversations.some((c) => c.id === activeId);
  const target = saved ? activeId : null;

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const here = readConversationIdFromPath(window.location.pathname, prefix);
    const previous = shownId.current;
    shownId.current = target;
    if (here === target) return;
    if (target === null && here !== null && previous === undefined) return;
    const path = target === null ? rootPath : `${prefix}${encodeURIComponent(target)}`;
    const sameChat = previous === null && activeId !== null && target === activeId;
    if (previous === undefined || sameChat) window.history.replaceState(window.history.state, '', path);
    else window.history.pushState(window.history.state, '', path);
  }, [target, activeId, prefix, rootPath]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const onPop = () => {
      const id = readConversationIdFromPath(window.location.pathname, prefix);
      shownId.current = id;
      onNavigateRef.current(id);
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, [prefix]);
}
