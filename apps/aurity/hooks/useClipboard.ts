/**
 * useClipboard Hook
 *
 * Reutilizable hook para copiar texto al clipboard con feedback visual.
 * Extraído de ConversationCapture durante refactoring incremental.
 *
 * @example
 * const { copiedId, copyToClipboard } = useClipboard();
 * <button onClick={() => copyToClipboard(sessionId, 'session')}>
 *   {copiedId === 'session' ? <Check /> : <Copy />}
 * </button>
 */

import { useState, useCallback } from 'react';

interface UseClipboardReturn {
  copiedId: string | null;
  copyToClipboard: (text: string, label: string) => Promise<void>;
}

export function useClipboard(timeout = 2000): UseClipboardReturn {
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const copyToClipboard = useCallback(
    async (text: string, label: string) => {
      try {
        await navigator.clipboard.writeText(text);
        setCopiedId(label);
        setTimeout(() => setCopiedId(null), timeout);
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    },
    [timeout]
  );

  return { copiedId, copyToClipboard };
}
