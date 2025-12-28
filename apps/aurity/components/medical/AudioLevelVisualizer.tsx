/**
 * AudioLevelVisualizer Component
 *
 * Real-time audio level analysis with stats grid.
 *
 * Features:
 * - Audio level bar with threshold indicator
 * - Voice activity detection (speaking/silence)
 * - Stats grid (duration, words, chunks)
 * - Visual quality feedback
 *
 * Extracted from ConversationCapture (Phase 7)
 */

import { formatTime } from '@/lib/audio/formatting';
import { AUDIO_CONFIG } from '@/lib/audio/constants';

interface AudioLevelVisualizerProps {
  audioLevel: number;
  recordingTime: number;
  wordCount: number;
  chunkCount: number;
}

export function AudioLevelVisualizer({
  audioLevel,
  recordingTime,
  wordCount,
  chunkCount,
}: AudioLevelVisualizerProps) {
  const isSpeaking = audioLevel > AUDIO_CONFIG.SILENCE_THRESHOLD;
  const percentLevel = Math.round((audioLevel / 255) * 100);
  const thresholdPercent = Math.round((AUDIO_CONFIG.SILENCE_THRESHOLD / 255) * 100);

  const getQualityIndicator = () => {
    if (audioLevel > AUDIO_CONFIG.SILENCE_THRESHOLD * 3) return '🟢 Excelente';
    if (audioLevel > AUDIO_CONFIG.SILENCE_THRESHOLD) return '🟡 Buena';
    return '🔴 Baja';
  };

  return (
    <div className="fi-card-xl animate-in">
      <div className="flex items-center justify-between mb-4">
        <h3 className="fi-title">Análisis de Audio en Vivo</h3>
        {/* Voice Activity Indicator */}
        <div className="fi-flex-gap">
          {isSpeaking ? (
            <>
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-xs fi-text-success font-medium">Hablando</span>
            </>
          ) : (
            <>
              <div className="w-2 h-2 bg-slate-500 rounded-full" />
              <span className="fi-text-xs-muted">Silencio</span>
            </>
          )}
        </div>
      </div>

      {/* Audio Level Bar with Threshold Indicator */}
      <div className="space-y-2 mb-6">
        <div className="flex items-center justify-between text-sm">
          <span className="fi-text">Nivel de audio</span>
          <span className="fi-text-success font-mono font-bold">
            {percentLevel}%
          </span>
        </div>
        <div className="relative w-full bg-slate-700 rounded-full h-3 overflow-hidden">
          {/* Audio level bar */}
          <div
            className={`h-3 rounded-full transition-all duration-100 ${
              isSpeaking
                ? 'bg-gradient-to-r from-emerald-500 via-cyan-500 to-purple-500'
                : 'bg-slate-600'
            }`}
            style={{ width: `${percentLevel}%` }}
          />
          {/* Threshold indicator line */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-yellow-400/50"
            style={{ left: `${thresholdPercent}%` }}
          />
        </div>
        <div className="flex items-center justify-between fi-text-xs-muted">
          <span>Umbral: {thresholdPercent}%</span>
          <span>{getQualityIndicator()}</span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-3">
        <div className="fi-card-dark text-center">
          <div className="text-2xl font-bold fi-text-info">{formatTime(recordingTime)}</div>
          <div className="fi-text-xs mt-1">Duración</div>
        </div>
        <div className="fi-card-dark text-center">
          <div className="text-2xl font-bold fi-text-success">
            {wordCount}
          </div>
          <div className="fi-text-xs mt-1">Palabras transcritas</div>
        </div>
        <div className="fi-card-dark text-center">
          <div className="text-2xl font-bold fi-text-purple">
            {chunkCount}
          </div>
          <div className="fi-text-xs mt-1">Segmentos (3s)</div>
        </div>
      </div>
    </div>
  );
}
