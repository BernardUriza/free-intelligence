"use client";

/**
 * Chat Page - AURITY Free Intelligence
 *
 * Standalone chat page using AppTemplate for consistent header with admin pages.
 * Uses the unified ChatWidget component in embedded mode.
 *
 * - If authenticated → memory enabled (infinite conversation)
 * - If anonymous → ephemeral mode (session-based, no backend persistence)
 */

import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { ChatWidget } from '@/components/chat/ChatWidget';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { chatHeader } from '@/config/page-headers';
import { defaultChatConfig, type ChatConfig } from '@/config/chat.config';

/**
 * Generates the configuration for the fullscreen chat page.
 * Since AppTemplate handles the header, we don't need title/subtitle here.
 */
const getChatConfig = (): Partial<ChatConfig> => ({
  ...defaultChatConfig,
  title: 'Free Intelligence', // Kept for internal reference
  subtitle: '', // Header handled by AppTemplate
  footer: undefined, // No footer to maximize space
  dimensions: {
    width: '100%',
    height: '100%', // Fill AppTemplate container
    minHeight: '100%',
    maxHeight: '100%',
  },
  behavior: {
    ...defaultChatConfig.behavior,
    inputPlaceholder: 'Escribe... (presiona Enter para enviar)',
  },
});

/**
 * Renders the standalone chat page.
 *
 * Uses AppTemplate for consistent header styling (glass morphism, back button).
 * ChatWidget runs in embedded mode (no internal header).
 */
export default function ChatPage() {
  const { user, isLoading } = useAuth();

  // Don't render until auth state is determined to avoid flicker
  if (isLoading) {
    return null;
  }

  const headerConfig = chatHeader({ isAuthenticated: !!user });
  const chatConfig = getChatConfig();

  return (
    <AppTemplate
      headerConfig={headerConfig}
      backgroundGradient="none"
      padding="0"
      maxWidth="full"
      fullHeight={true}
      showWatermark={false}
      showGeometricBg={false}
    >
      <ChatWidget
        config={chatConfig}
        initialOpen={true}
        initialMode="fullscreen"
        embedded={true}
      />
    </AppTemplate>
  );
}
