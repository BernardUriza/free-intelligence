/**
 * ToastContainer - Renders toast notifications
 *
 * Displays toast notifications in a fixed position overlay.
 * Works with the useToast hook.
 */

'use client';

import { useEffect, useState } from 'react';
import { Toast, TOAST_STYLES } from '@/hooks/useToast';

interface ToastContainerProps {
  toasts: Toast[];
  onRemove: (id: string) => void;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left' | 'top-center';
}

const POSITION_CLASSES: Record<string, string> = {
  'top-right': 'top-4 right-4',
  'top-left': 'top-4 left-4',
  'bottom-right': 'bottom-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'top-center': 'top-4 left-1/2 -translate-x-1/2',
};

export function ToastContainer({
  toasts,
  onRemove,
  position = 'top-right',
}: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <div
      className={`fixed z-50 fi-stack-sm ${POSITION_CLASSES[position]}`}
      role="region"
      aria-label="Notificaciones"
      aria-live="polite"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>
  );
}

interface ToastItemProps {
  toast: Toast;
  onRemove: (id: string) => void;
}

function ToastItem({ toast, onRemove }: ToastItemProps) {
  const [isExiting, setIsExiting] = useState(false);
  const styles = TOAST_STYLES[toast.type];

  // Handle exit animation
  const handleRemove = () => {
    setIsExiting(true);
    setTimeout(() => onRemove(toast.id), 200);
  };

  // Auto-remove effect handled by useToast, but we can add exit animation
  useEffect(() => {
    if (toast.duration && toast.duration > 0) {
      const exitTimer = setTimeout(() => setIsExiting(true), toast.duration - 200);
      return () => clearTimeout(exitTimer);
    }
  }, [toast.duration]);

  return (
    <div
      className={`
        flex items-center gap-3 px-4 py-3 rounded-lg border backdrop-blur-sm
        shadow-lg min-w-[280px] max-w-[400px]
        transform transition-all duration-200 ease-out
        ${styles.bg} ${styles.border}
        ${isExiting ? 'opacity-0 translate-x-4' : 'opacity-100 translate-x-0'}
        animate-in slide-in-from-right-4
      `}
      role="alert"
    >
      {/* Icon */}
      <span className={`text-lg ${styles.text}`}>{styles.icon}</span>

      {/* Message */}
      <p className={`flex-1 text-sm font-medium ${styles.text}`}>
        {toast.message}
      </p>

      {/* Close button */}
      <button
        onClick={handleRemove}
        className={`p-1 rounded hover:bg-white/10 transition-colors ${styles.text}`}
        aria-label="Cerrar notificación"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
  );
}
