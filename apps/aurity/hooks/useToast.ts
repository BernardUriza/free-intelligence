/**
 * useToast - Simple toast notification hook
 *
 * Provides a lightweight toast notification system for the dashboard.
 * No external dependencies required.
 */

import { useState, useCallback, useRef } from 'react';

export interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
  duration?: number;
}

interface UseToastOptions {
  /** Default duration for toasts (ms) */
  defaultDuration?: number;
  /** Maximum number of toasts to show at once */
  maxToasts?: number;
}

export function useToast(options: UseToastOptions = {}) {
  const { defaultDuration = 3000, maxToasts = 3 } = options;
  const [toasts, setToasts] = useState<Toast[]>([]);
  const toastIdRef = useRef(0);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message: string, type: Toast['type'] = 'info', duration?: number) => {
      const id = `toast-${++toastIdRef.current}`;
      const toast: Toast = {
        id,
        message,
        type,
        duration: duration ?? defaultDuration,
      };

      setToasts((prev) => {
        const newToasts = [...prev, toast];
        // Remove oldest if exceeding maxToasts
        if (newToasts.length > maxToasts) {
          return newToasts.slice(-maxToasts);
        }
        return newToasts;
      });

      // Auto-remove after duration
      if (toast.duration && toast.duration > 0) {
        setTimeout(() => removeToast(id), toast.duration);
      }

      return id;
    },
    [defaultDuration, maxToasts, removeToast]
  );

  const success = useCallback(
    (message: string, duration?: number) => addToast(message, 'success', duration),
    [addToast]
  );

  const error = useCallback(
    (message: string, duration?: number) => addToast(message, 'error', duration),
    [addToast]
  );

  const info = useCallback(
    (message: string, duration?: number) => addToast(message, 'info', duration),
    [addToast]
  );

  const warning = useCallback(
    (message: string, duration?: number) => addToast(message, 'warning', duration),
    [addToast]
  );

  const clear = useCallback(() => setToasts([]), []);

  return {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    info,
    warning,
    clear,
  };
}

/**
 * Toast type styling configuration
 */
export const TOAST_STYLES: Record<Toast['type'], {
  bg: string;
  border: string;
  text: string;
  iconKey: string;
}> = {
  success: {
    bg: 'bg-emerald-500/20',
    border: 'border-emerald-500/50',
    text: 'text-emerald-300',
    iconKey: 'success',
  },
  error: {
    bg: 'bg-red-500/20',
    border: 'border-red-500/50',
    text: 'text-red-300',
    iconKey: 'error',
  },
  info: {
    bg: 'bg-blue-500/20',
    border: 'border-blue-500/50',
    text: 'text-blue-300',
    iconKey: 'info',
  },
  warning: {
    bg: 'bg-amber-500/20',
    border: 'border-amber-500/50',
    text: 'text-amber-300',
    iconKey: 'warning',
  },
};
