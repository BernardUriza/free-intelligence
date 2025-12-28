'use client';

/**
 * ProtectedChatWidget - Chat Widget with Auth0 Protection
 *
 * Wrapper que asegura que el ChatWidget esté envuelto por Auth0Provider.
 * Resuelve el error "You forgot to wrap your component in <Auth0Provider>".
 */

import { Auth0Provider } from '../auth/Auth0Provider';
import { ChatWidget } from './ChatWidget';
import type { ChatConfig } from '@/config/chat.config';

export interface ProtectedChatWidgetProps {
  /** Configuración opcional del chat */
  config?: Partial<ChatConfig>;
}

export function ProtectedChatWidget({ config }: ProtectedChatWidgetProps) {
  return (
    <Auth0Provider>
      <ChatWidget config={config} />
    </Auth0Provider>
  );
}

export default ProtectedChatWidget;