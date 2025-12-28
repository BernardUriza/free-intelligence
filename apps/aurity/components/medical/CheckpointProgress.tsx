/**
 * CheckpointProgress Component
 *
 * Shows visual progress when creating a checkpoint (pause action).
 *
 * Features:
 * - Progress bar animation
 * - Status messages
 * - Chunk count display
 * - Audio size display
 *
 * Created: 2025-11-15
 */

import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

interface CheckpointProgressProps {
  isCreating: boolean;
  isSuccess: boolean;
  isError: boolean;
  chunksCount?: number;
  audioSizeMB?: number;
  errorMessage?: string;
}

export function CheckpointProgress({
  isCreating,
  isSuccess,
  isError,
  chunksCount,
  audioSizeMB,
  errorMessage,
}: CheckpointProgressProps) {
  if (!isCreating && !isSuccess && !isError) {
    return null;
  }

  return (
    <div className="bg-slate-700/50 rounded-lg p-4 border border-slate-600 animate-slide-up">
      <div className="fi-flex-gap-md">
        {isCreating && (
          <>
            <Loader2 className="h-5 w-5 fi-text-info animate-spin flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium fi-text-info">Creando checkpoint...</p>
              <p className="fi-text-xs mt-1">
                Concatenando {chunksCount || 0} chunks de audio
              </p>
            </div>
          </>
        )}

        {isSuccess && !isCreating && (
          <>
            <CheckCircle2 className="h-5 w-5 fi-text-green flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium fi-text-green">Checkpoint creado</p>
              <p className="fi-text-xs mt-1">
                {chunksCount || 0} chunks concatenados ({audioSizeMB?.toFixed(2) || 0} MB)
              </p>
            </div>
          </>
        )}

        {isError && (
          <>
            <AlertCircle className="h-5 w-5 fi-text-error flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium fi-text-error">Error al crear checkpoint</p>
              <p className="fi-text-xs mt-1">{errorMessage || 'Error desconocido'}</p>
            </div>
          </>
        )}
      </div>

      {/* Progress bar - only when creating */}
      {isCreating && (
        <div className="mt-3 w-full bg-slate-600 rounded-full h-1.5 overflow-hidden">
          <div className="h-full bg-cyan-400 animate-pulse" style={{ width: '100%' }} />
        </div>
      )}
    </div>
  );
}
