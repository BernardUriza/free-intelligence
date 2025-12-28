/**
 * PausedAudioPreview Component
 *
 * Audio player shown when recording is paused, with concatenated audio preview.
 *
 * Features:
 * - Audio player for concatenated segments
 * - "Finalizar Sesión" button
 * - Visual indicator of paused state
 * - Segment count display
 *
 * Created: Phase 7 Enhancement (2025-11-13)
 */

import { StopCircle, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PausedAudioPreviewProps {
  audioUrl: string | null;
  segmentCount: number;
  chunkCount: number;
  onEndSession: () => void;
  onResume: () => void;
}

export function PausedAudioPreview({
  audioUrl,
  segmentCount,
  chunkCount,
  onEndSession,
  onResume,
}: PausedAudioPreviewProps) {
  return (
    <div className="fi-card-warning animate-in fade-in duration-300">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-2 h-2 rounded-full bg-yellow-400" />
        <h3 className="fi-title">
          Grabación Pausada
        </h3>
        <span className="text-xs ml-auto text-yellow-400">
          {chunkCount} chunks procesados
        </span>
      </div>

      {/* Audio Player - Only if audio available */}
      {audioUrl ? (
        <div className="fi-card-yellow mb-4">
          <p className="text-sm text-white font-semibold mb-3">
            🎧 Audio grabado ({segmentCount} segmento{segmentCount !== 1 ? 's' : ''})
          </p>
          <audio
            controls
            src={audioUrl}
            className="w-full"
            preload="auto"
            style={{
              minHeight: '54px',
              backgroundColor: '#1e293b',
              borderRadius: '8px',
            }}
          />
        </div>
      ) : (
        <div className="fi-card-red mb-4">
          <p className="text-sm fi-text-error">
            ⚠️ Audio no disponible (audioUrl: {audioUrl === null ? 'null' : 'undefined'})
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="fi-flex-gap-md">
        <Button
          onClick={onResume}
          variant="success"
          size="lg"
          icon={Play}
          fullWidth
          className="shadow-lg"
        >
          Continuar Grabando
        </Button>

        <Button
          onClick={onEndSession}
          variant="danger"
          size="lg"
          icon={StopCircle}
          fullWidth
          className="shadow-lg"
        >
          Finalizar Sesión
        </Button>
      </div>

      <div className="mt-3 flex items-center gap-2 text-xs text-yellow-400">
        <span>⏸️ Puedes escuchar el audio grabado o continuar grabando</span>
      </div>
    </div>
  );
}
