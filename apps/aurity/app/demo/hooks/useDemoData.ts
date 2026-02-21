import { useState, useEffect, useCallback } from 'react';

import type { DemoSession, ConfirmAction, StatusMessage } from '../types';
import { DEMO_STORAGE_KEY, DEMO_LOADED_KEY } from '../constants';
import { generateDemoSessions } from '../data/demo-sessions';

export interface UseDemoDataReturn {
  isLoaded: boolean;
  sessions: DemoSession[];
  isLoading: boolean;
  showConfirm: ConfirmAction;
  message: StatusMessage | null;
  setShowConfirm: (action: ConfirmAction) => void;
  handleLoadDemo: () => Promise<void>;
  handleResetDemo: () => Promise<void>;
}

/** Manages demo dataset lifecycle: load from localStorage, persist, and reset. */
export function useDemoData(): UseDemoDataReturn {
  const [isLoaded, setIsLoaded] = useState(false);
  const [sessions, setSessions] = useState<DemoSession[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState<ConfirmAction>(null);
  const [message, setMessage] = useState<StatusMessage | null>(null);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const loaded = localStorage.getItem(DEMO_LOADED_KEY);
    if (loaded === 'true') {
      const stored = localStorage.getItem(DEMO_STORAGE_KEY);
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          setSessions(parsed);
          setIsLoaded(true);
        } catch {
          localStorage.removeItem(DEMO_STORAGE_KEY);
          localStorage.removeItem(DEMO_LOADED_KEY);
        }
      }
    }
  }, []);

  const handleLoadDemo = useCallback(async () => {
    setIsLoading(true);
    setMessage(null);

    try {
      await new Promise((resolve) => setTimeout(resolve, 1500));

      const demoSessions = generateDemoSessions();

      localStorage.setItem(DEMO_STORAGE_KEY, JSON.stringify(demoSessions));
      localStorage.setItem(DEMO_LOADED_KEY, 'true');

      setSessions(demoSessions);
      setIsLoaded(true);
      setShowConfirm(null);
      setMessage({ type: 'success', text: 'Demo dataset loaded successfully! 3 sessions with 30 events total.' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to load demo dataset. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleResetDemo = useCallback(async () => {
    setIsLoading(true);
    setMessage(null);

    try {
      await new Promise((resolve) => setTimeout(resolve, 800));

      localStorage.removeItem(DEMO_STORAGE_KEY);
      localStorage.removeItem(DEMO_LOADED_KEY);

      setSessions([]);
      setIsLoaded(false);
      setShowConfirm(null);
      setMessage({ type: 'success', text: 'Demo dataset cleared. All demo data has been removed.' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to reset demo dataset.' });
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    isLoaded,
    sessions,
    isLoading,
    showConfirm,
    message,
    setShowConfirm,
    handleLoadDemo,
    handleResetDemo,
  };
}
