/**
 * H5 Debug Tools Hook
 *
 * Development-only hook for HDF5 session inspection.
 *
 * Features:
 * - Keyboard shortcut: Ctrl+Shift+H
 * - Fetch H5 data from backend
 * - Only enabled in development mode
 *
 * Author: Bernard Uriza Orozco
 * Created: 2025-11-15
 */

import { useState, useEffect, useCallback } from 'react';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
const isDevelopment = process.env.NODE_ENV === 'development';

interface H5Data {
  session_id: string;
  chunks?: Array<{
    index: number;
    transcript?: string;
    latency_ms?: number;
    status: string;
  }>;
  transcription_full: string;
  word_count: number;
  duration_seconds: number;
  avg_latency_ms?: number;
  wpm: number;
  full_audio_available: boolean;
}

export function useH5DebugTools(sessionId: string | null) {
  const [isOpen, setIsOpen] = useState(false);
  const [h5Data, setH5Data] = useState<H5Data | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchH5Data = useCallback(async () => {
    if (!sessionId || !isDevelopment) {
      console.warn('[H5Debug] Not available in production or no session ID');
      return;
    }

    setIsLoading(true);
    try {
      console.log(`[H5Debug] Fetching HDF5 data for session: ${sessionId}`);
      const response = await fetch(
        `${BACKEND_URL}/api/workflows/aurity/sessions/${sessionId}/h5-data`,
        {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setH5Data(data);
      setIsOpen(true);
      console.log('[H5Debug] ✅ H5 data loaded successfully');
    } catch (error) {
      console.error('[H5Debug] ❌ Error fetching H5 data:', error);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  // Keyboard shortcut: Ctrl+Shift+H
  useEffect(() => {
    if (!isDevelopment) return;

    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.ctrlKey && event.shiftKey && event.key === 'H') {
        event.preventDefault();
        console.log('[H5Debug] 🔑 Hotkey triggered: Ctrl+Shift+H');
        fetchH5Data();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [fetchH5Data]);

  const close = useCallback(() => {
    setIsOpen(false);
  }, []);

  return {
    isOpen,
    h5Data,
    isLoading,
    fetchH5Data,
    close,
    isEnabled: isDevelopment,
  };
}
