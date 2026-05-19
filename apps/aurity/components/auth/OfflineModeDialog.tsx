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
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('OfflineMode');

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
      log.error('Failed to enable offline mode', { error: String(error) });
    } finally {
      setIsConfirming(false);
    }
  };

  const limitations = getOfflineModeLimitations();

  return (
    <div className="offline-overlay">
      <div
        className="offline-dialog"
        role="dialog"
        aria-labelledby="offline-dialog-title"
        aria-describedby="offline-dialog-description"
      >
        {/* Header */}
        <div className="offline-header">
          <div className="offline-header-icon">
            <WifiOff className="w-6 h-6 text-amber-400" />
          </div>
          <div>
            <h2
              id="offline-dialog-title"
              className="offline-title"
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
          <div className="offline-warning-card">
            <div className="offline-warning-row">
              <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="offline-warning-title">Limitaciones:</p>
                <ul className="space-y-1.5">
                  {limitations.map((limitation, index) => (
                    <li
                      key={index}
                      className="offline-limitation-item"
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
          <div className="offline-notice">
            <Clock className="w-4 h-4" />
            <span>El modo offline expira en 24 horas</span>
          </div>

          {/* Security notice */}
          <div className="offline-notice-secure">
            <Shield className="w-4 h-4" />
            <span>Tus datos locales permanecen seguros y encriptados</span>
          </div>
        </div>

        {/* Actions */}
        <div className="offline-actions">
          <button
            onClick={onCancel}
            disabled={isConfirming}
            className="offline-btn-cancel"
          >
            {reason === 'auth_unavailable' ? 'Reintentar' : 'Cancelar'}
          </button>
          <button
            onClick={handleConfirm}
            disabled={isConfirming}
            className="offline-btn-confirm"
          >
            {isConfirming ? (
              <>
                <div className="offline-spinner" />
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
