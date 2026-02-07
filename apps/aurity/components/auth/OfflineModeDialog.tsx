'use client';

/**
 * OfflineModeDialog - Confirmation dialog for enabling offline mode
 *
 * Shown when:
 * 1. Auth server is unreachable during login attempt
 * 2. User explicitly requests offline mode
 *
 * Requires explicit user confirmation with clear explanation of limitations.
 * This is a security measure to ensure users understand the implications.
 */

import { useState } from 'react';
import { AlertTriangle, WifiOff, Shield, Clock } from 'lucide-react';
import {
  enableOfflineMode,
  getOfflineModeLimitations,
} from '@/lib/auth/offline-mode';

interface OfflineModeDialogProps {
  /**
   * Callback when user confirms offline mode
   */
  onConfirm: () => void;

  /**
   * Callback when user cancels (wants to retry auth)
   */
  onCancel: () => void;

  /**
   * Reason for showing the dialog
   */
  reason: 'auth_unavailable' | 'user_requested';

  /**
   * Whether the dialog is visible
   */
  isOpen: boolean;
}

export function OfflineModeDialog({
  onConfirm,
  onCancel,
  reason,
  isOpen,
}: OfflineModeDialogProps) {
  const [isConfirming, setIsConfirming] = useState(false);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    setIsConfirming(true);
    try {
      await enableOfflineMode(reason);
      onConfirm();
    } catch (error) {
      console.error('[OfflineModeDialog] Failed to enable offline mode:', error);
    } finally {
      setIsConfirming(false);
    }
  };

  const limitations = getOfflineModeLimitations();

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div
        className="bg-slate-900 border border-amber-500/40 rounded-xl p-6 max-w-md w-full shadow-2xl"
        role="dialog"
        aria-labelledby="offline-dialog-title"
        aria-describedby="offline-dialog-description"
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-amber-500/20 rounded-lg">
            <WifiOff className="w-6 h-6 text-amber-400" />
          </div>
          <div>
            <h2
              id="offline-dialog-title"
              className="text-xl font-semibold text-white"
            >
              Modo Offline
            </h2>
            <p className="text-sm text-slate-400">
              {reason === 'auth_unavailable'
                ? 'Servidor de autenticación no disponible'
                : 'Trabajar sin conexión'}
            </p>
          </div>
        </div>

        {/* Description */}
        <div id="offline-dialog-description" className="space-y-4">
          <p className="text-slate-300 text-sm">
            {reason === 'auth_unavailable'
              ? 'No se puede conectar con el servidor de autenticación. Puedes continuar en modo offline con funcionalidad limitada.'
              : 'Has solicitado trabajar en modo offline. Algunas funciones no estarán disponibles.'}
          </p>

          {/* Limitations warning */}
          <div className="bg-amber-900/20 border border-amber-500/30 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-amber-200 mb-2">Limitaciones:</p>
                <ul className="space-y-1.5">
                  {limitations.map((limitation, index) => (
                    <li
                      key={index}
                      className="text-sm text-amber-100/80 flex items-start gap-2"
                    >
                      <span className="text-amber-400 mt-1">•</span>
                      {limitation}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* Expiration notice */}
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Clock className="w-4 h-4" />
            <span>El modo offline expira en 24 horas</span>
          </div>

          {/* Security notice */}
          <div className="flex items-center gap-2 text-sm text-emerald-400">
            <Shield className="w-4 h-4" />
            <span>Tus datos locales permanecen seguros y encriptados</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 mt-6">
          <button
            onClick={onCancel}
            disabled={isConfirming}
            className="flex-1 px-4 py-2.5 rounded-lg border border-slate-600 text-slate-300
                       hover:bg-slate-800 hover:border-slate-500 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {reason === 'auth_unavailable' ? 'Reintentar' : 'Cancelar'}
          </button>
          <button
            onClick={handleConfirm}
            disabled={isConfirming}
            className="flex-1 px-4 py-2.5 rounded-lg bg-amber-600 text-white font-medium
                       hover:bg-amber-500 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed
                       flex items-center justify-center gap-2"
          >
            {isConfirming ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Activando...
              </>
            ) : (
              'Continuar Offline'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook to manage offline mode dialog state
 */
export function useOfflineModeDialog() {
  const [isOpen, setIsOpen] = useState(false);
  const [reason, setReason] = useState<'auth_unavailable' | 'user_requested'>(
    'auth_unavailable'
  );

  const show = (dialogReason: 'auth_unavailable' | 'user_requested') => {
    setReason(dialogReason);
    setIsOpen(true);
  };

  const hide = () => {
    setIsOpen(false);
  };

  return {
    isOpen,
    reason,
    show,
    hide,
  };
}
