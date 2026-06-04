// @free-intelligence/core · voice engine contract
//
// Mirrors the StreamAdapter philosophy: the contract lives in core, the
// implementations live in the apps. fi-glass consumes ONLY this interface and
// stays backend-agnostic — it never knows about Azure, OpenAI, endpoints, auth,
// or session ids. An app implements VoiceAdapter once against its own backend
// and passes the instance to the voice UI.

/**
 * Audio produced by synthesize().
 *
 * - `Blob`        → a fully-rendered clip; fi-glass calls URL.createObjectURL.
 * - `{ url }`     → a ready (possibly streaming) URL; fi-glass uses it directly.
 *
 * Supporting both keeps streaming TTS (hear-while-generating) open without
 * forcing every backend to stream.
 */
export type AudioSource = Blob | { url: string };

/** A selectable TTS voice offered by the adapter. */
export interface VoiceOption {
  /** Stable id passed back to synthesize() (e.g. "nova", "en-US-AvaNeural"). */
  id: string;
  /** Human label for the picker (e.g. "Nova"). */
  label: string;
  /** Optional group header for the picker (e.g. "OpenAI", "Azure Neural"). */
  group?: string;
}

/** Result of transcribing one recorded audio chunk. */
export interface TranscriptResult {
  /** Recognized text for this chunk (may be empty). */
  text: string;
}

/** Metadata fi-glass passes alongside each transcription chunk. */
export interface TranscribeContext {
  /**
   * 0-based index of this chunk within the current recording. A streaming
   * adapter uses it for session/ordering; a one-shot adapter (single chunk on
   * stop) simply ignores it.
   */
  index: number;
  /** Lets the app abort the in-flight request when recording stops. */
  signal?: AbortSignal;
}

/**
 * VoiceAdapter — the app's voice engine, injected whole into fi-glass.
 *
 * Capabilities are a la carte (all members optional):
 *   - no adapter          -> no voice (UI hides mic + speak)
 *   - synthesize present  -> TTS available (SpeakButton + AudioPlayer)
 *   - transcribe present  -> STT available (VoiceMicButton dictation)
 *
 * Add a new capability by adding an optional member here — never by threading a
 * new callback through the components.
 */
export interface VoiceAdapter {
  // ---- TTS (output) ----
  /** Synthesize speech for `text` in an optional voice id; resolves to audio. */
  synthesize?(text: string, voice?: string): Promise<AudioSource>;
  /** Voices offered in the player's picker. */
  readonly availableVoices?: VoiceOption[];
  /** Voice id used when the caller doesn't specify one. */
  readonly defaultVoice?: string;

  // ---- STT (input) ----
  /** Transcribe one recorded audio chunk to text. */
  transcribe?(chunk: Blob, ctx?: TranscribeContext): Promise<TranscriptResult>;
}
