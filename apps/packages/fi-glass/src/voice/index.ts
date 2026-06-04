// fi-glass · voice (Americio, element 95 — slice 2, presentation layer).
// Pure presentational primitives: recording controls + the chat mic button.
// Engine hooks (useRecorder/useAudioAnalysis) and the VoiceAdapter-consuming
// orchestration (useVoice/useDictation) land here next.
export * from './recording';
export { VoiceMicButton } from './VoiceMicButton';

// Californio (98): TTS trigger button (presentation only; app owns playback).
export { SpeakButton, type SpeakButtonProps } from './SpeakButton';

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
