/**
 * StreamingTranscript Component
 *
 * Real-time streaming transcription display with last chunk highlighting.
 *
 * Features:
 * - Live transcription updates
 * - Last chunk highlight animation (cyan background)
 * - Blinking cursor effect (only when active)
 * - Paused state indicator
 * - Chunk count indicator
 *
 * Extracted from ConversationCapture (Phase 7)
 * Updated: Pause state support (2025-11-13)
 */

import type { TranscriptionData } from '@aurity-standalone/hooks/useTranscription';

interface StreamingTranscriptProps {
  transcriptionData: TranscriptionData;
  lastChunkText: string;
  chunkCount: number;
  isPaused?: boolean;
}

export function StreamingTranscript({
  transcriptionData,
  lastChunkText,
  chunkCount,
  isPaused = false,
}: StreamingTranscriptProps) {
  if (!transcriptionData?.text) return null;

  return (
    <div className={isPaused ? 'fi-card-streaming-paused' : 'fi-card-streaming-active'}>
      <div className="fi-flex-gap mb-4">
        <div className={isPaused ? 'fi-dot-streaming-paused' : 'fi-dot-streaming-active'} />
        <h3 className="fi-title">
          {isPaused ? 'Transcripción (Pausada)' : 'Transcripción en Tiempo Real'}
        </h3>
        <span className={isPaused ? 'fi-counter-streaming-paused' : 'fi-counter-streaming-active'}>
          {chunkCount} chunks procesados
        </span>
      </div>

      <div className="fi-card-cyan">
        <p className="fi-text whitespace-pre-wrap leading-relaxed">
          {/* Render old text */}
          {transcriptionData.text.substring(0, transcriptionData.text.length - lastChunkText.length)}
          {/* Highlight last chunk with fade-in animation */}
          {lastChunkText && (
            <span className="animate-in fade-in duration-500 bg-cyan-500/20 rounded px-0.5">
              {lastChunkText}
            </span>
          )}
          {/* Blinking cursor - Only when NOT paused */}
          {!isPaused && <span className="fi-cursor-blink" />}
        </p>
      </div>

      <div className="mt-3 fi-flex-gap fi-text-xs">
        <span>{isPaused ? '⏸️ Grabación pausada - texto preservado' : '💡 El texto se actualiza cada 3 segundos mientras hablas'}</span>
      </div>
    </div>
  );
}
