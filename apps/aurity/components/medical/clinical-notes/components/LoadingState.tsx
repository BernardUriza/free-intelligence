'use client';

import { memo } from 'react';
import { Loader2 } from 'lucide-react';
import type { SOAPGenerationStatus } from '../types';
import { POLLING_CONFIG } from '../constants';

interface LoadingStateProps {
  status: SOAPGenerationStatus;
  attempts: number;
  maxAttempts?: number;
}

export const LoadingState = memo(function LoadingState({
  status,
  attempts,
  maxAttempts = POLLING_CONFIG.maxAttempts,
}: LoadingStateProps) {
  const statusMessages: Record<NonNullable<SOAPGenerationStatus>, string> = {
    pending: 'Esperando generación de SOAP...',
    in_progress: `Generando notas SOAP con IA... (${attempts}/${maxAttempts})`,
    completed: 'Cargando notas SOAP...',
    error: 'Error al cargar notas...',
  };

  return (
    <div className="fi-empty-state">
      <Loader2
        className="h-12 w-12 fi-text-primary animate-spin"
        aria-hidden="true"
      />
      <span className="mt-4 text-slate-400" role="status" aria-live="polite">
        {status ? statusMessages[status] : 'Cargando notas clínicas...'}
      </span>
      {status === 'in_progress' && (
        <div
          className="mt-4 w-64 bg-slate-700 rounded-full h-2"
          role="progressbar"
          aria-valuenow={attempts}
          aria-valuemin={0}
          aria-valuemax={maxAttempts}
        >
          <div
            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${(attempts / maxAttempts) * 100}%` }}
          />
        </div>
      )}
    </div>
  );
});
