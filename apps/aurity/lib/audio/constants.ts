/**
 * Audio Constants
 *
 * Configuración centralizada para grabación y procesamiento de audio.
 * Extraído de ConversationCapture durante refactoring incremental.
 */

export const AUDIO_CONFIG = {
  // Silence detection threshold (0-255 scale, average across frequencies)
  // Values below this threshold will be considered silence and skipped
  // Recommended range: 2-15 (2 = very sensitive, 15 = less sensitive)
  // Lowered to 2 for conversational speech (medical dialogue typically 2-4% avg)
  SILENCE_THRESHOLD: 2,

  // Audio gain multiplier for low-gain microphones
  // 1.0 = no amplification, 2.0 = double, 3.0 = triple
  AUDIO_GAIN: 2.5,

  // Chunk time slice in milliseconds (8 seconds per chunk)
  TIME_SLICE: 8000,

  // Audio recording configuration
  SAMPLE_RATE: 16000,
  CHANNELS: 1,

  // Job polling configuration
  POLL_INTERVAL: 500, // 500ms between polls
  MAX_POLL_ATTEMPTS: 120, // 120 attempts * 500ms = 60s timeout
} as const;
