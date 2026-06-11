// fi-glass · voice (Americio, element 95 — slice 2, presentation layer).
// Pure presentational primitives: recording controls + the chat mic button.
// Engine hooks (useRecorder/useAudioAnalysis) and the VoiceAdapter-consuming
// orchestration (useVoice/useDictation) land here next.
export * from './recording';
export { VoiceMicButton } from './VoiceMicButton';

// Californio (98): TTS trigger button (presentation only; app owns playback).
export { SpeakButton, type SpeakButtonProps } from './SpeakButton';

// B3-VOICE-FIGLASS-1: reusable TTS playback foundation. The missing half of the
// voice stack — synthesis resolves an AudioSource, this plays it (and owns the
// object-URL cleanup). Headless engine + React hook + presentational controls.
export {
  createAudioPlayer,
  type AudioPlayerController,
  type AudioPlayerOptions,
  type AudioPlayerState,
  type AudioPlayerStatus,
  type AudioElementLike,
} from './createAudioPlayer';
export {
  useAudioPlayer,
  type UseAudioPlayerOptions,
  type UseAudioPlayerReturn,
} from './useAudioPlayer';
export { AudioPlayer, type AudioPlayerProps } from './AudioPlayer';

// B3-VOICE-FIGLASS-2: rich voice controls + reusable visualizers. Additive over
// the B3-VOICE-FIGLASS-1 foundation — the minimal AudioPlayer is untouched. og118
// is the canary that surfaced the austere player / missing visualizer / no mic
// slot; these primitives raise that UX to the framework. No STT, no backend.
export {
  RichAudioPlayer,
  formatPlaybackTime,
  type RichAudioPlayerProps,
} from './RichAudioPlayer';
export {
  AudioVisualizer,
  normalizeLevels,
  resampleLevels,
  type AudioVisualizerProps,
  type AudioVisualizerVariant,
} from './AudioVisualizer';
export {
  ComposerMicSlot,
  type ComposerMicSlotProps,
} from './ComposerMicSlot';

// Orchestration that consumes a VoiceAdapter (Americio slice 2).
export {
  useVoice,
  type UseVoiceOptions,
  type UseVoiceReturn,
} from './useVoice';
export {
  useDictation,
  type UseDictationOptions,
  type UseDictationReturn,
} from './useDictation';

// Engine primitives (pure Web Audio) — apps can use these or bring their own.
export { useRecorder } from './useRecorder';
export { useAudioAnalysis } from './useAudioAnalysis';
export { makeRecorder } from './makeRecorder';

// B3-VOICE-FIGLASS-9: durable local audio capture queue.
// Separates capture (useDurableRecording) from transcription (useAudioQueue).
// Audio persists in IndexedDB until transcribed or explicitly deleted.
export {
  type AudioArtifact,
  type StoredAudioArtifact,
  type AudioArtifactState,
  type AudioQueuePolicy,
  AUDIO_QUEUE_DEFAULTS,
  makeArtifactId,
  isPending,
  isTerminal,
  artifactLabel,
  formatArtifactSize,
  formatArtifactDuration,
} from './audioArtifact';
export {
  AudioQueueStore,
  type AudioQueueStoreOptions,
} from './AudioQueueStore';
export {
  useDurableRecording,
  type UseDurableRecordingOptions,
  type UseDurableRecordingReturn,
} from './useDurableRecording';
export {
  useAudioQueue,
  type UseAudioQueueOptions,
  type UseAudioQueueReturn,
} from './useAudioQueue';
export {
  AudioQueuePanel,
  type AudioQueuePanelProps,
} from './AudioQueuePanel';
export {
  AudioQueueItem,
  type AudioQueueItemProps,
} from './AudioQueueItem';
