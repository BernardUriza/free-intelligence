'use client';

/**
 * Ultra-compact Toast System
 * 
 * Specs:
 * - Max 320px width
 * - 48px height
 * - No /internal/ paths leaked
 * - Human-friendly messages only
 * - Bottom-right position
 * - Auto-dismiss 4s
 */

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { X, AlertCircle, CheckCircle2, Info } from 'lucide-react';

export type ToastType = 'error' | 'success' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  message: string;
}

// ToastProps exported for external usage
export type ToastProps = Toast;

interface ToastContextValue {
  toasts: Toast[];
  showToast: (type: ToastType, message: string) => void;
  dismissToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((type: ToastType, message: string) => {
    const id = Math.random().toString(36).slice(2, 11);
    const toast: Toast = { id, type, message };
    
    setToasts(prev => [...prev, toast]);

    // Auto-dismiss after 4s
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, showToast, dismissToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within ToastProvider');
  }
  return context;
}

// Toast Container (bottom-right)
function ToastContainer({ 
  toasts, 
  onDismiss 
}: { 
  toasts: Toast[];
  onDismiss: (id: string) => void;
}) {
  return (
    <div className="fixed bottom-4 right-4 z-[9999] fi-stack-sm pointer-events-none">
      {toasts.map(toast => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

// Individual Toast
function ToastItem({ 
  toast, 
  onDismiss 
}: { 
  toast: Toast;
  onDismiss: (id: string) => void;
}) {
  const icons = {
    error: AlertCircle,
    success: CheckCircle2,
    info: Info,
  };

  const styles = {
    error: 'bg-red-950/90 border-red-500/30 text-red-200',
    success: 'bg-emerald-950/90 border-emerald-500/30 text-emerald-200',
    info: 'bg-blue-950/90 border-blue-500/30 text-blue-200',
  };

  const Icon = icons[toast.type];

  return (
    <div
      className={`
        pointer-events-auto
        w-80 h-12
        flex items-center gap-2
        px-3 py-2
        ${styles[toast.type]}
        border backdrop-blur-2xl
        rounded-xl
        shadow-xl
        animate-slide-in-right
      `}
      role="alert"
      aria-live="assertive"
    >
      <Icon className="w-4 h-4 flex-shrink-0" />
      <p className="flex-1 text-xs font-[450] leading-tight truncate">
        {toast.message}
      </p>
      <button
        onClick={() => onDismiss(toast.id)}
        className="flex-shrink-0 p-1 hover:bg-white/10 rounded transition-colors"
        aria-label="Cerrar"
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}

/**
 * Helper: Sanitize error messages
 * Remove /internal/ paths, technical details
 */
export function sanitizeErrorMessage(error: unknown): string {
  let message = '';

  if (error instanceof Error) {
    message = error.message;
  } else if (typeof error === 'string') {
    message = error;
  } else {
    message = 'Ocurrió un error inesperado';
  }

  // Remove /internal/ paths
  message = message.replace(/\/internal\/[^\s]*/g, '[endpoint]');
  
  // Remove technical stack traces
  message = message.split('\n')[0];

  // Humanize common errors
  const humanMessages: Record<string, string> = {
    'network error': 'Error de conexión. Verifica tu internet.',
    'timeout': 'La solicitud tardó demasiado. Reintenta.',
    'unauthorized': 'Sesión expirada. Inicia sesión nuevamente.',
    'not found': 'Recurso no encontrado.',
    'server error': 'Error del servidor. Reintenta en unos momentos.',
    'failed to fetch': 'No pudimos conectar con el servidor.',
  };

  const lowerMessage = message.toLowerCase();
  for (const [key, human] of Object.entries(humanMessages)) {
    if (lowerMessage.includes(key)) {
      return human;
    }
  }

  // Truncate if too long
  if (message.length > 80) {
    return message.slice(0, 77) + '...';
  }

  return message;
}
