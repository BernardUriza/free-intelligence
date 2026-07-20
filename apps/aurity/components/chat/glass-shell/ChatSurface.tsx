'use client';

/**
 * fi-glass · ChatSurface — the full-page, chat-first composition.
 *
 * Where <ChatWidget> is a floating bubble (FloatingButton when closed, view
 * modes, minimize/maximize), ChatSurface is for apps where the chat IS the page
 * (e.g. og118 at `/`). It mounts ALWAYS OPEN, renders NO FloatingButton and NO
 * close affordance, and fills its parent — the page owns the height (wrap it in
 * a full-height container, e.g. `h-dvh`).
 *
 * It is NOT a fork: internally it is <ChatWidget> pinned to the embedded +
 * open + fullscreen view, so it reuses ChatWidgetContainer's view-mode/
 * breakpoint math verbatim. The only thing it removes is the launcher.
 *
 * Pairs with the optional ChatWidgetProps (a hello-chat passes only chatHook +
 * message/onMessageChange/onSend; voice/upload/persona/response-mode are omitted
 * and the toolbar hides them).
 */

import type { ChatMessage } from '@free-intelligence/core';
import { ChatWidget } from './ChatWidget';
import type { ChatWidgetProps } from './types';

/**
 * Same surface as ChatWidget minus the launcher/view-mode knobs, which
 * ChatSurface fixes to the always-open full-page configuration.
 */
export type ChatSurfaceProps<TMessage = ChatMessage, TNode = unknown> = Omit<
  ChatWidgetProps<TMessage, TNode>,
  'initialOpen' | 'embedded' | 'initialMode'
>;

export function ChatSurface<TMessage = ChatMessage, TNode = unknown>(
  props: ChatSurfaceProps<TMessage, TNode>
) {
  return (
    <ChatWidget<TMessage, TNode>
      {...props}
      embedded
      initialOpen
      initialMode="fullscreen"
    />
  );
}
