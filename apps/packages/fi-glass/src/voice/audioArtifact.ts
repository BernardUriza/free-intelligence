// B3-VOICE-FIGLASS-9 — Audio artifact types and policy contract.
// An AudioArtifact is a local audio capture with a stable identity, real MIME type,
// and a state machine that separates recording from transcription.

export type AudioArtifactState =
  | 'recording'
  | 'paused'
  | 'stopping'    // async stop in-flight (RecordRTC + IndexedDB save, ~500ms)
  | 'saved'
  | 'queued'
  | 'uploading'
  | 'transcribing'
  | 'transcribed'
  | 'failed'
  | 'deleted';

export interface AudioArtifact {
  id: string;
  mime: string;
  size: number;
  durationMs?: number;
  createdAt: string;
  updatedAt: string;
  state: AudioArtifactState;
  transcript?: string;
  errorMessage?: string;
}

// Full record stored in IndexedDB (blob stored natively, not base64).
export interface StoredAudioArtifact extends AudioArtifact {
  blob: Blob;
}

export interface AudioQueuePolicy {
  maxItems: number;
  maxBytes: number;
  maxBytesPerItem: number;
}

export const AUDIO_QUEUE_DEFAULTS: AudioQueuePolicy = {
  maxItems: 10,
  maxBytes: 50 * 1024 * 1024,      // 50 MB total queue
  maxBytesPerItem: 10 * 1024 * 1024, // 10 MB per artifact
};

export function makeArtifactId(): string {
  return `audio-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function isPending(a: AudioArtifact): boolean {
  return a.state !== 'transcribed' && a.state !== 'deleted';
}

export function isTerminal(a: AudioArtifact): boolean {
  return a.state === 'transcribed' || a.state === 'deleted';
}

export function artifactLabel(state: AudioArtifactState): string {
  const map: Record<AudioArtifactState, string> = {
    recording: 'Grabando',
    paused: 'En pausa',
    stopping: 'Guardando...',
    saved: 'Guardado',
    queued: 'En cola',
    uploading: 'Subiendo',
    transcribing: 'Transcribiendo',
    transcribed: 'Transcrito',
    failed: 'Falló',
    deleted: 'Eliminado',
  };
  return map[state];
}

export function formatArtifactSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatArtifactDuration(ms?: number): string {
  if (!ms) return '--:--';
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}
