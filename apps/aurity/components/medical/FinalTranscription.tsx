/**
 * FinalTranscription Component
 *
 * Final transcription display with audio playback and continue button.
 *
 * Features:
 * - Completed transcription text
 * - Full audio playback (WebM)
 * - Continue button with loading state
 * - Chunk count indicator
 *
 * Extracted from ConversationCapture (Phase 7)
 */

import { CheckCircle, Bell } from 'lucide-react';
import type { TranscriptionData } from '@aurity-standalone/hooks/useTranscription';
import { Button } from '@/components/ui/button';

interface FinalTranscriptionProps {
  transcriptionData: TranscriptionData;
  fullAudioUrl: string | null;
  chunkCount: number;
  onContinue?: () => void;
}

export function FinalTranscription({
  transcriptionData,
  fullAudioUrl,
  chunkCount,
  onContinue,
}: FinalTranscriptionProps) {
  // Always show the component after recording, even if no transcription
  const hasTranscription = transcriptionData?.text && transcriptionData.text.trim().length > 0;

  return (
    <div className="fi-card-xl">
      <div className="fi-flex-gap mb-4">
        <CheckCircle className="h-5 w-5 fi-text-green" />
        <h3 className="fi-title">Transcripción Completada</h3>
      </div>

      <div className="bg-slate-900/50 rounded-lg p-4 mb-4">
        {hasTranscription ? (
          <p className="fi-text-pre">{transcriptionData.text}</p>
        ) : (
          <div className="text-center py-6">
            <p className="text-slate-500 mb-2">⚠️ No se generó transcripción</p>
            <p className="text-xs text-slate-600">
              Posibles causas: audio muy bajo, silencio detectado, o problema con el micrófono
            </p>
          </div>
        )}
      </div>

      {/* Audio Playback (DEMO REQUIREMENT) - Show when audio is available */}
      {fullAudioUrl && (
        <div className="fi-card-success mb-4">
          <div className="fi-flex-gap mb-3">
            <Bell className="fi-icon-md fi-icon-emerald" />
            <h4 className="fi-title-sm">Audio Completo</h4>
            <span className="ml-auto fi-text-xs">
              {chunkCount} chunks grabados
            </span>
          </div>
          <audio
            controls
            className="w-full"
            src={fullAudioUrl}
            preload="metadata"
          >
            Tu navegador no soporta reproducción de audio.
          </audio>
          <div className="mt-2 fi-text-xs">
            💡 Puedes reproducir el audio completo de la consulta
          </div>
        </div>
      )}

      {onContinue && (
        <Button
          onClick={onContinue}
          variant="primary"
          size="lg"
          fullWidth
        >
          Continuar al Siguiente Paso
        </Button>
      )}
    </div>
  );
}
