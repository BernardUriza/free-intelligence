'use client';

// B3-VOICE-FIGLASS-9 — Reusable audio queue panel.
// Lists all pending audio artifacts with state, actions, and a privacy notice.
// Consumers wire it to useAudioQueue + useDurableRecording.

import { useEffect, useState } from 'react';
import { Loader2, Trash2, Info } from 'lucide-react';
import type { UseAudioQueueReturn } from './useAudioQueue';
import { AudioQueueItem } from './AudioQueueItem';
import { formatArtifactSize } from './audioArtifact';

export interface AudioQueuePanelProps {
  queue: UseAudioQueueReturn;
  /** CSS class applied to the root container */
  className?: string;
  /** Privacy notice text. Defaults to a generic local-storage notice. */
  privacyNotice?: string;
  /** How long the privacy notice stays visible, in ms. 0 keeps it forever.
   * Default 35s — it is recurring info, not a warning the user must dismiss. */
  privacyNoticeMs?: number;
  /** Max visible items before scroll */
  maxVisible?: number;
  /** Artifact ids to hide from the panel (e.g. the active draft shown inline
   * via AudioDraftPlayer, so it is not duplicated in the backlog list). */
  excludeIds?: string[];
}

const DEFAULT_PRIVACY_NOTICE =
  'Tu audio se guarda localmente hasta que lo transcribas o elimines. No se envía al servidor hasta que lo solicites.';

const DEFAULT_PRIVACY_NOTICE_MS = 35_000;

export function AudioQueuePanel({
  queue,
  className = '',
  privacyNotice = DEFAULT_PRIVACY_NOTICE,
  privacyNoticeMs = DEFAULT_PRIVACY_NOTICE_MS,
  maxVisible = 6,
  excludeIds = [],
}: AudioQueuePanelProps) {
  const {
    artifacts,
    isLoading,
    transcribeArtifact,
    retryTranscription,
    deleteArtifact,
    clearTranscribed,
    getPlaybackUrl,
  } = queue;

  // The notice is informational and recurring — auto-hide it instead of
  // squatting the composer area forever.
  const [showNotice, setShowNotice] = useState(true);
  useEffect(() => {
    if (!privacyNoticeMs) return;
    const t = setTimeout(() => setShowNotice(false), privacyNoticeMs);
    return () => clearTimeout(t);
  }, [privacyNoticeMs]);

  const visible = artifacts.filter(
    (a) => a.state !== 'deleted' && !excludeIds.includes(a.id),
  );
  const hasTranscribed = visible.some((a) => a.state === 'transcribed');
  // The header describes what the list SHOWS, so it must sum the same set.
  // (queue.totalBytes is the capacity metric: pending-only, transcribed
  // excluded — using it here read "1 audio · 0 B" for a transcribed item.)
  const visibleBytes = visible.reduce((s, a) => s + a.size, 0);

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
      {/* Privacy notice — informational (blue), auto-hides */}
      {showNotice && (
        <div className="fi-audio-queue-notice flex items-start gap-2 px-3 py-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
          <Info className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
          <p className="text-[11px] text-blue-200/70 leading-relaxed">
            {privacyNotice}
          </p>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between px-1">
        <span className="text-xs text-white/50">
          {visible.length} audio{visible.length !== 1 ? 's' : ''} · {formatArtifactSize(visibleBytes)}
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
