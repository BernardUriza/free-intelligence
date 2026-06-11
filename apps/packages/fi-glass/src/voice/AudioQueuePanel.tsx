'use client';

// B3-VOICE-FIGLASS-9 — Reusable audio queue panel.
// Lists all pending audio artifacts with state, actions, and a privacy notice.
// Consumers wire it to useAudioQueue + useDurableRecording.

import { Loader2, Trash2, ShieldAlert } from 'lucide-react';
import type { UseAudioQueueReturn } from './useAudioQueue';
import { AudioQueueItem } from './AudioQueueItem';
import { formatArtifactSize } from './audioArtifact';

export interface AudioQueuePanelProps {
  queue: UseAudioQueueReturn;
  /** CSS class applied to the root container */
  className?: string;
  /** Privacy notice text. Defaults to a generic local-storage notice. */
  privacyNotice?: string;
  /** Max visible items before scroll */
  maxVisible?: number;
}

const DEFAULT_PRIVACY_NOTICE =
  'Tu audio se guarda localmente hasta que lo transcribas o elimines. No se envía al servidor hasta que lo solicites.';

export function AudioQueuePanel({
  queue,
  className = '',
  privacyNotice = DEFAULT_PRIVACY_NOTICE,
  maxVisible = 6,
}: AudioQueuePanelProps) {
  const {
    artifacts,
    totalBytes,
    isLoading,
    transcribeArtifact,
    retryTranscription,
    deleteArtifact,
    clearTranscribed,
    getPlaybackUrl,
  } = queue;

  const visible = artifacts.filter((a) => a.state !== 'deleted');
  const hasTranscribed = visible.some((a) => a.state === 'transcribed');

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center p-4 ${className}`}>
        <Loader2 className="w-4 h-4 text-white/40 animate-spin" />
      </div>
    );
  }

  if (visible.length === 0) return null;

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Privacy notice */}
      <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
        <ShieldAlert className="w-3.5 h-3.5 text-yellow-400 shrink-0 mt-0.5" />
        <p className="text-[11px] text-yellow-200/70 leading-relaxed">
          {privacyNotice}
        </p>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between px-1">
        <span className="text-xs text-white/50">
          {visible.length} audio{visible.length !== 1 ? 's' : ''} · {formatArtifactSize(totalBytes)}
        </span>
        {hasTranscribed && (
          <button
            onClick={clearTranscribed}
            className="flex items-center gap-1 text-xs text-white/40 hover:text-white/70 transition-colors"
          >
            <Trash2 className="w-3 h-3" />
            Limpiar transcritos
          </button>
        )}
      </div>

      {/* Items */}
      <div
        className="space-y-1.5 overflow-y-auto"
        style={{ maxHeight: `${maxVisible * 68}px` }}
      >
        {visible.map((artifact) => (
          <AudioQueueItem
            key={artifact.id}
            artifact={artifact}
            onTranscribe={transcribeArtifact}
            onRetry={retryTranscription}
            onDelete={deleteArtifact}
            onGetPlaybackUrl={getPlaybackUrl}
          />
        ))}
      </div>
    </div>
  );
}
