'use client';

/**
 * ProtectedChatWidget - Chat Widget with Auth Protection
 *
 * Wrapper que asegura que el ChatWidget esté envuelto por AuthProvider.
 */

import { AuthProvider } from '../auth/AuthProvider';
import { ChatWidget } from './ChatWidget';
import type { ChatConfig } from '@/config/chat.config';

export interface ProtectedChatWidgetProps {
  /** Configuración opcional del chat */
  config?: Partial<ChatConfig>;
}

export function ProtectedChatWidget({ config }: ProtectedChatWidgetProps) {
  return (
    <AuthProvider>
      <ChatWidget config={config} />
    </AuthProvider>
  );
}

export default ProtectedChatWidget;