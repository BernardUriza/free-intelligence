import * as react from 'react';
import { LucideIcon } from 'lucide-react';
import { AudioSource, VoiceAdapter } from '@free-intelligence/core';

/**
 * Shared Recording Component Types
 *
 * Common types and configurations for recording UI components.
 * Used by: RecordingControls, VoiceMicButton, and future recording UIs.
 */

/**
 * Universal recording state enum.
 * All recording components should use these states.
 */
type RecordingStateType = 'idle' | 'starting' | 'recording' | 'pausing' | 'paused' | 'resuming' | 'processing' | 'stopping' | 'finalized';
type ButtonSize = 'sm' | 'md' | 'lg' | 'xl';
interface ButtonSizeConfig {
    button: string;
    icon: string;
    ring?: string;
}
declare const BUTTON_SIZES: Record<ButtonSize, ButtonSizeConfig>;
type ColorTheme = 'medical' | 'chat' | 'minimal';
interface StateColors {
    idle: string;
    starting: string;
    recording: string;
    pausing: string;
    paused: string;
    resuming: string;
    processing: string;
    stopping: string;
    finalized: string;
}
declare const COLOR_THEMES: Record<ColorTheme, StateColors>;
type PulseStyle = 'none' | 'ping' | 'rings' | 'vad';
interface PulseConfig {
    style: PulseStyle;
    color?: string;
    audioLevel?: number;
    isSilent?: boolean;
}
interface StatusTextConfig {
    idle: string;
    starting: string;
    recording: string;
    pausing: string;
    paused: string;
    resuming: string;
    processing: string;
    stopping: string;
    finalized: string;
}
declare const STATUS_TEXT_ES: StatusTextConfig;
declare const STATUS_TEXT_EN: StatusTextConfig;

interface RecordingButtonProps {
    /** Button size variant */
    size?: ButtonSize;
    /** Background color (domain class) */
    bgColor: string;
    /** Icon to display */
    icon: LucideIcon;
    /** Whether icon should spin (for loading states) */
    iconSpin?: boolean;
    /** Icon color (domain class, default: rec-icon-white) */
    iconColor?: string;
    /** Whether button is disabled */
    disabled?: boolean;
    /** Click handler */
    onClick: () => void;
    /** Accessibility label */
    ariaLabel: string;
    /** Additional button classes */
    className?: string;
    /** Border/ring styles for accessibility */
    borderStyle?: string;
    /** Animation classes (e.g., animate-heartbeat) */
    animate?: string;
}
declare const RecordingButton: react.ForwardRefExoticComponent<RecordingButtonProps & react.RefAttributes<HTMLButtonElement>>;

interface PulseRingsProps {
    /** Animation style */
    style: PulseStyle;
    /** Ring color name (e.g. 'yellow-500') */
    color?: string;
    /** Audio level 0-255 for VAD style */
    audioLevel?: number;
    /** Whether audio is silent (for VAD color switching) */
    isSilent?: boolean;
    /** Additional container classes */
    className?: string;
}
declare function PulseRings({ style, color, audioLevel, isSilent, className, }: PulseRingsProps): react.JSX.Element | null;

/**
 * RecordingTimer - Shared Timer Display Component
 *
 * Displays recording time in MM:SS format.
 * Used by: RecordingControls, VoiceMicButton
 *
 * Features:
 * - Multiple size variants
 * - Optional recording dot indicator
 * - Configurable colors
 */
interface RecordingTimerProps {
    /** Time in seconds */
    time: number;
    /** Whether to show the timer */
    visible?: boolean;
    /** Size variant */
    size?: 'sm' | 'md' | 'lg';
    /** Show blinking recording dot */
    showDot?: boolean;
    /** Text color (domain class) */
    textColor?: string;
    /** Dot color (domain class) */
    dotColor?: string;
    /** Additional classes */
    className?: string;
}
/**
 * Format seconds to MM:SS string
 */
declare function formatRecordingTime(seconds: number): string;
declare function RecordingTimer({ time, visible, size, showDot, textColor, dotColor, className, }: RecordingTimerProps): react.JSX.Element | null;

/**
 * StatusText - Recording Status Display Component
 *
 * Shows current recording status with optional loader.
 * Used by: RecordingControls, VoiceMicButton
 */
interface StatusTextProps {
    /** Status message to display */
    text: string;
    /** Text color (domain class) */
    color?: string;
    /** Show loading spinner */
    showLoader?: boolean;
    /** Animate with pulse effect */
    animate?: boolean;
    /** Additional classes */
    className?: string;
}
declare function StatusText({ text, color, showLoader, animate, className, }: StatusTextProps): react.JSX.Element;

/**
 * VoiceMicButton Component
 *
 * Compact microphone button for chat with VAD (Voice Activity Detection).
 * Uses shared recording primitives from ./recording.
 *
 * Features:
 * - VAD rings that respond to audio level
 * - Color feedback: green (voice), red (silent)
 * - Compact design for chat toolbar
 * - Recording timer display
 *
 * Refactored: 2025-12-11 - Uses shared recording primitives
 */
interface VoiceMicButtonProps {
    isRecording: boolean;
    isTranscribing: boolean;
    audioLevel: number;
    isSilent: boolean;
    recordingTime: number;
    onStart: () => void;
    onStop: () => void;
    className?: string;
}
declare function VoiceMicButton({ isRecording, isTranscribing, audioLevel, isSilent, recordingTime, onStart, onStop, className, }: VoiceMicButtonProps): react.JSX.Element;

interface SpeakButtonProps {
    /** Text to speak. */
    content: string;
    /** Voice id (e.g. "nova"); shown in the tooltip. */
    voice?: string;
    /** Whether this is a user message (lets the player offer voice selection). */
    isUserMessage?: boolean;
    /** Open/play handler — provided by the app's audio player. */
    onOpenPlayer: (text: string, voice: string, isUserMessage?: boolean) => void;
    /**
     * Synthesis in flight (B3-VOICE-FIGLASS-6): renders a spinner instead of the
     * speaker, disables the button and sets aria-busy. TTS takes seconds; a
     * silent button reads as dead and invites paid spam clicks. Wire it to
     * `useVoice.isLoading` (scoped to this message via `currentText`).
     */
    busy?: boolean;
    /**
     * The clip is already in the session cache (B3-VOICE-FIGLASS-8): clicking
     * replays instantly and bills nothing. Renders a Play icon instead of the
     * speaker so the user can tell "already generated" from "will synthesize
     * (paid, takes seconds)". Wire it to `useVoice.hasCachedAudio(content, voice)`.
     * `busy` takes precedence while a synthesis is in flight.
     */
    cached?: boolean;
    /** Size preset (drives default padding + icon size). */
    size?: 'xs' | 'sm' | 'md';
    /** Override the button class entirely (e.g. aurity's exact legacy string). */
    className?: string;
    /** Override the icon class. */
    iconClassName?: string;
    /** Override the tooltip (default: "Escuchar (<voice>)"). */
    title?: string;
    /** Tooltip while busy (default: "Generando audio…"). */
    busyTitle?: string;
    /** Tooltip when the clip is cached (default: "Reproducir (ya generado)"). */
    cachedTitle?: string;
}
declare function SpeakButton({ content, voice, isUserMessage, onOpenPlayer, busy, cached, size, className, iconClassName, title, busyTitle, cachedTitle, }: SpeakButtonProps): react.JSX.Element;

/**
 * fi-glass · audioPlayer — the reusable TTS *playback* engine (headless).
 *
 * The missing half of the voice stack: `useVoice`/SpeakButton resolve an
 * `AudioSource` (synthesis), but nothing in fi-glass actually PLAYS it — every
 * consumer (aurity, and next og118) had to re-wire its own <audio>, play/stop,
 * loading/error and object-URL cleanup. This engine owns that lifecycle once so
 * apps inherit it instead of re-implementing it.
 *
 * Deliberately framework-agnostic and dependency-injected: it talks to an
 * `AudioElementLike` (defaults to `new Audio()`) and to the object-URL helpers,
 * so the whole state machine — including URL-leak cleanup — is unit-testable in
 * node with a fake element and zero DOM. The React `useAudioPlayer` hook and the
 * `<AudioPlayer>` component are thin shells over this.
 *
 * Ownership rule (avoids the leak in useVoice.close): the engine revokes ONLY
 * the object URLs it created itself (from a Blob). A `{ url }` source is owned by
 * the caller / kept open for streaming, so it is never revoked here.
 */

type AudioPlayerStatus = 'idle' | 'loading' | 'playing' | 'paused' | 'error';
interface AudioPlayerState {
    status: AudioPlayerStatus;
    isPlaying: boolean;
    isLoading: boolean;
    error: Error | null;
    /** The URL currently loaded into the element (object URL or external url). */
    currentSrc: string | null;
    /** Seconds; 0 until metadata loads. */
    duration: number;
    currentTime: number;
}
/**
 * The slice of HTMLAudioElement the engine touches. Real playback passes a
 * `new Audio()`; tests pass a fake that drives the same events synchronously.
 */
interface AudioElementLike {
    src: string;
    currentTime: number;
    readonly duration: number;
    readonly paused: boolean;
    play(): Promise<void>;
    pause(): void;
    load(): void;
    addEventListener(type: string, listener: () => void): void;
    removeEventListener(type: string, listener: () => void): void;
}
interface AudioPlayerDeps {
    /** Build the audio element. Default: `() => new Audio()` (browser only). */
    createElement?: () => AudioElementLike;
    /** Default: `URL.createObjectURL`. */
    createObjectURL?: (blob: Blob) => string;
    /** Default: `URL.revokeObjectURL`. */
    revokeObjectURL?: (url: string) => void;
}
interface AudioPlayerOptions extends AudioPlayerDeps {
    /** Called on a playback/load error (app owns logging/reporting). */
    onError?: (error: unknown, context: string) => void;
    /** Called once when the current clip finishes. */
    onEnded?: () => void;
}
interface AudioPlayerController {
    getState(): AudioPlayerState;
    /** Subscribe to state changes; returns an unsubscribe fn. */
    subscribe(listener: () => void): () => void;
    /** Point the player at a new source (revokes any previously-owned URL). */
    load(source: AudioSource): void;
    /** Start/resume playback of the loaded source. */
    play(): Promise<void>;
    pause(): void;
    /** Stop, rewind to 0 and release any owned object URL. */
    stop(): void;
    /** Play if paused/idle, pause if playing. */
    toggle(): Promise<void>;
    /**
     * Jump to an absolute position in seconds, clamped to [0, duration] (or
     * [0, seconds] while duration is still unknown). Drives the rich progress
     * bar / scrubber. No-op after dispose or before a source is loaded.
     */
    seek(seconds: number): void;
    /**
     * Move the playhead by a relative delta in seconds (negative = rewind),
     * clamped like `seek`. Powers the "back 10s / forward 10s" controls.
     */
    seekBy(deltaSeconds: number): void;
    /** Tear down: detach listeners, pause, release owned URL. Idempotent. */
    dispose(): void;
}
declare function createAudioPlayer(options?: AudioPlayerOptions): AudioPlayerController;

interface UseAudioPlayerOptions {
    onError?: (error: unknown, context: string) => void;
    onEnded?: () => void;
    /**
     * Dependency overrides forwarded to the engine. Apps never need these; tests
     * and non-DOM environments inject a fake element / URL helpers.
     */
    deps?: Pick<AudioPlayerOptions, 'createElement' | 'createObjectURL' | 'revokeObjectURL'>;
}
interface UseAudioPlayerReturn extends AudioPlayerState {
    /** Point the player at a source without starting it. */
    load: (source: AudioSource) => void;
    play: () => Promise<void>;
    pause: () => void;
    stop: () => void;
    toggle: () => Promise<void>;
    /** Jump to an absolute position (seconds), clamped to [0, duration]. */
    seek: (seconds: number) => void;
    /** Move the playhead by a relative delta (seconds); negative rewinds. */
    seekBy: (deltaSeconds: number) => void;
    /** Convenience: load a source and immediately play it. */
    playSource: (source: AudioSource) => Promise<void>;
}
declare function useAudioPlayer(opts?: UseAudioPlayerOptions): UseAudioPlayerReturn;

interface AudioPlayerProps {
    /** Audio to play; when it changes the player loads the new source. */
    source?: AudioSource | null;
    /** Start playing as soon as a new source loads. Default false. */
    autoPlay?: boolean;
    /** Called on a playback/load error. */
    onError?: (error: unknown, context: string) => void;
    /** Called when the clip finishes. */
    onEnded?: () => void;
    /** Override the wrapper class. */
    className?: string;
    /** Override the button class (applies to both buttons). */
    buttonClassName?: string;
    /** Override the icon class. */
    iconClassName?: string;
}
declare function AudioPlayer({ source, autoPlay, onError, onEnded, className, buttonClassName, iconClassName, }: AudioPlayerProps): react.JSX.Element;

interface RichAudioPlayerProps {
    /** Audio to play; when it changes the player loads the new source. */
    source?: AudioSource | null;
    /** Start playing as soon as a new source loads. Default false. */
    autoPlay?: boolean;
    /** Seconds the skip-back / skip-forward controls jump. Default 10. */
    skipSeconds?: number;
    /**
     * Compact transport for tight spaces (CONV-MOBILE-RECLAIM / voice-note preview
     * in the mobile composer). Drops the skip-back / stop / skip-forward buttons —
     * keeping only play-pause + scrubber + a SINGLE time readout — so the row fits
     * a phone-width composer beside a primary action (Transcribir / Guardar)
     * instead of pushing it off-screen. The full four-button transport (default)
     * stays for the standalone TTS player where the width is available.
     */
    compact?: boolean;
    /** Show the time readout. Default true. */
    showTime?: boolean;
    /** Called on a playback/load error. */
    onError?: (error: unknown, context: string) => void;
    /** Called when the clip finishes. */
    onEnded?: () => void;
    /** Override the wrapper class. */
    className?: string;
    /** Override the button class (applies to all transport buttons). */
    buttonClassName?: string;
    /** Override the icon class. */
    iconClassName?: string;
    /** Override the progress scrubber class. */
    progressClassName?: string;
}
/**
 * Format seconds as mm:ss (or h:mm:ss past an hour). Pure + exported so the
 * readout formatting is unit-tested without rendering. Guards NaN/negatives
 * (duration is NaN until metadata loads) by collapsing them to 0:00.
 */
declare function formatPlaybackTime(seconds: number): string;
declare function RichAudioPlayer({ source, autoPlay, skipSeconds, compact, showTime, onError, onEnded, className, buttonClassName, iconClassName, progressClassName, }: RichAudioPlayerProps): react.JSX.Element;

/**
 * fi-glass · AudioVisualizer — reusable audio-level graphic (bars / pulse).
 *
 * The visual half of the voice UX that AURITY had baked into its clinical
 * capture screen: animated bars and pulsing rings that react to audio level.
 * Extracted here as a pure, presentational primitive so any surface — a TTS
 * player, a recording composer, a future shell — can render levels without
 * pulling in Web Audio, a microphone, or the network.
 *
 * Deliberately data-driven: it renders whatever normalized `levels` (0..1) it
 * is handed. Real consumers feed it analyser output (e.g. `useAudioAnalysis`
 * scaled to 0..1); tests feed it a fixed array. No effects, no timers, no
 * randomness — same props in, same DOM out — so it is unit-testable with static
 * rendering and never depends on a live mic.
 *
 * Accessibility: it is a non-interactive graphic, exposed as role="img" with a
 * label so assistive tech announces it as a single "audio level" image rather
 * than a pile of empty divs.
 */
type AudioVisualizerVariant = 'bars' | 'pulse';
interface AudioVisualizerProps {
    /**
     * Normalized amplitude samples in [0, 1]. Out-of-range values are clamped.
     * For `bars`, each sample is one bar; for `pulse`, the peak drives the ring.
     */
    levels: number[];
    /** Visual style. Default 'bars'. */
    variant?: AudioVisualizerVariant;
    /**
     * Whether the source is actively producing audio. When false the graphic
     * renders at rest (flat bars / collapsed pulse) regardless of `levels`, so a
     * paused player or an idle mic reads as silent.
     */
    active?: boolean;
    /**
     * For `bars`: force a fixed bar count, resampling `levels` to fit. Defaults to
     * `levels.length`. Lets a surface keep a stable bar count across frames.
     */
    barCount?: number;
    /** Accessible label. Default 'Visualizador de nivel de audio'. */
    label?: string;
    /** Wrapper class. */
    className?: string;
    /** Per-bar class (bars variant). */
    barClassName?: string;
    /** Fill color applied inline (bars background / pulse border). */
    color?: string;
}
/** Clamp to [0,1] and drop non-finite values to 0. Pure + exported for tests. */
declare function normalizeLevels(levels: number[]): number[];
/**
 * Resample an array to exactly `count` points by nearest-index sampling. Pure +
 * exported so the resampling rule is unit-tested. Returns zeros for count<=0.
 */
declare function resampleLevels(levels: number[], count: number): number[];
declare function AudioVisualizer({ levels, variant, active, barCount, label, className, barClassName, color, }: AudioVisualizerProps): react.JSX.Element;

interface ComposerMicSlotProps {
    /**
     * Whether voice dictation is wired (an STT adapter exists). Default false →
     * the slot renders disabled/unavailable. No STT backend is required for the
     * slot itself; this flag is the consumer's declaration of capability.
     */
    available?: boolean;
    /** Currently capturing audio. */
    recording?: boolean;
    /** Transcribing / processing — shows a spinner and disables interaction. */
    busy?: boolean;
    /** Begin capture (consumer owns the recorder). Ignored when unavailable. */
    onStart?: () => void;
    /** Stop capture. Ignored when unavailable. */
    onStop?: () => void;
    /** Label/title shown while unavailable. */
    unavailableLabel?: string;
    /** aria-label for the start affordance. */
    startLabel?: string;
    /** aria-label for the stop affordance. */
    stopLabel?: string;
    /** aria-label while busy. */
    busyLabel?: string;
    /** Wrapper class. */
    className?: string;
    /** Button class. */
    buttonClassName?: string;
    /** Icon class. */
    iconClassName?: string;
}
declare function ComposerMicSlot({ available, recording, busy, onStart, onStop, unavailableLabel, startLabel, stopLabel, busyLabel, className, buttonClassName, iconClassName, }: ComposerMicSlotProps): react.JSX.Element;

interface UseVoiceOptions {
    /** Called when synthesis fails (app decides logging/reporting). */
    onError?: (error: unknown, context: string) => void;
}
interface UseVoiceReturn {
    isOpen: boolean;
    isLoading: boolean;
    audioUrl: string | null;
    voiceName: string;
    isUserMessage: boolean;
    currentVoice: string;
    currentText: string;
    generateAudio: (text: string, voice?: string, isUser?: boolean) => Promise<void>;
    changeVoice: (newVoice: string) => Promise<void>;
    close: () => void;
    /**
     * Whether `text` (+`voice`, default 'nova') is already in the session cache —
     * i.e. clicking Speak would replay instantly and bill nothing. Lets the UI
     * tell "will synthesize (paid, seconds)" apart from "already generated"
     * (B3-VOICE-FIGLASS-8). Render-time freshness is guaranteed by the state
     * updates every synthesis already makes (isLoading/audioUrl).
     */
    hasCachedAudio: (text: string, voice?: string) => boolean;
}
declare function useVoice(adapter: VoiceAdapter | undefined, opts?: UseVoiceOptions): UseVoiceReturn;

interface UseDictationOptions {
    /** Chunk interval in ms handed to the recorder (default 30s). */
    timeSliceMs?: number;
    /** Specific audio input device id. */
    deviceId?: string | null;
    /** Called with the full accumulated transcript on each chunk. */
    onTranscriptUpdate?: (full: string) => void;
    /** Called on recording/transcription failure. */
    onError?: (message: string) => void;
}
interface UseDictationReturn {
    isRecording: boolean;
    recordingTime: number;
    audioLevel: number;
    isSilent: boolean;
    /** Live, normalized (0..1) frequency bands — feed AudioVisualizer `levels`. */
    bands: number[];
    liveTranscript: string;
    isTranscribing: boolean;
    startRecording: () => Promise<void>;
    stopRecording: () => Promise<void>;
}
declare function useDictation(adapter: VoiceAdapter | undefined, opts?: UseDictationOptions): UseDictationReturn;

/**
 * useRecorder Hook
 *
 * Maneja la grabación de audio con arquitectura dual recorder:
 * - Chunked recorder: Para transcripción en tiempo real (chunks de 3s)
 * - Continuous recorder: Para audio completo sin chunks (playback final)
 *
 * Extraído de ConversationCapture durante refactoring incremental.
 *
 * @example
 * const { isRecording, recordingTime, startRecording, stopRecording, fullAudioBlob, currentStream } =
 *   useRecorder({
 *     onChunk: async (blob, chunkNumber) => {
 *       // Process chunk (upload, transcribe, etc.)
 *     },
 *     onError: (error) => console.error(error)
 *   });
 */
interface UseRecorderConfig {
    onChunk: (blob: Blob, chunkNumber: number) => Promise<void> | void;
    onError?: (error: string) => void;
    timeSlice?: number;
    sampleRate?: number;
    channels?: number;
    /** Optional external MediaStream (e.g., from demo audio) instead of microphone */
    externalStream?: MediaStream | null;
    /** Specific audio input device ID (null = use system default) */
    deviceId?: string | null;
}
interface UseRecorderReturn {
    isRecording: boolean;
    recordingTime: number;
    currentStream: MediaStream | null;
    fullAudioBlob: Blob | null;
    fullAudioUrl: string | null;
    startRecording: () => Promise<void>;
    stopRecording: () => Promise<Blob | null>;
}
declare function useRecorder(config: UseRecorderConfig): UseRecorderReturn;

/**
 * useAudioAnalysis Hook
 *
 * Analiza el nivel de audio en tiempo real usando Web Audio API.
 * Incluye detección de silencio y control de ganancia.
 * Extraído de ConversationCapture durante refactoring incremental.
 *
 * @example
 * const { audioLevel, isSilent } = useAudioAnalysis(stream, {
 *   silenceThreshold: 5,
 *   gain: 2.5,
 *   isActive: isRecording
 * });
 */
interface AudioAnalysisConfig {
    silenceThreshold?: number;
    gain?: number;
    isActive: boolean;
    /** How many frequency bands to expose for a bar visualizer. Default 24. */
    bandCount?: number;
}
interface UseAudioAnalysisReturn {
    audioLevel: number;
    isSilent: boolean;
    /**
     * Normalized (0..1) frequency bands, downsampled from the analyser's spectrum
     * to `bandCount` entries. Empty + zeroed while inactive. Feed straight to
     * AudioVisualizer `levels` for a live equalizer that reacts to the voice's
     * pitch, not just its volume.
     */
    bands: number[];
}
declare function useAudioAnalysis(stream: MediaStream | null, config: AudioAnalysisConfig): UseAudioAnalysisReturn;

/**
 * RecordRTC-based Audio Recorder Factory
 *
 * Uses stop/start loop pattern to generate chunks with valid headers.
 * Each chunk is a COMPLETE recording with full EBML/WAV headers.
 *
 * Why RecordRTC only (no MediaRecorder fallback):
 * - MediaRecorder generates headerless chunks after chunk 0
 * - OpenAI Whisper rejects headerless chunks with 400 error
 * - A broken fallback is worse than a clear error
 *
 * File: apps/aurity/lib/recording/makeRecorder.ts
 * Updated: 2025-12-11 (Removed broken MediaRecorder fallback)
 */
type ChunkHandler = (blob: Blob) => void;
interface RecorderOptions {
    timeSlice?: number;
    sampleRate?: number;
    channels?: number;
}
interface Recorder {
    start: () => void;
    stop: () => Promise<Blob>;
    kind: 'recordrtc';
}
/**
 * Create audio recorder with chunk support using RecordRTC.
 *
 * Uses stop/start loop pattern:
 * 1. Record for N seconds
 * 2. Stop recording → generates complete file with headers
 * 3. Get blob → chunk has all headers (EBML/WAV)
 * 4. Start new recording → next chunk also complete
 *
 * @param stream MediaStream from getUserMedia
 * @param onChunk Callback for each chunk (timeslice interval)
 * @param opts Recording options
 * @returns Recorder instance
 * @throws Error if RecordRTC import fails
 */
declare function makeRecorder(stream: MediaStream, onChunk: ChunkHandler, opts?: RecorderOptions): Promise<Recorder>;

type AudioArtifactState = 'recording' | 'paused' | 'stopping' | 'saved' | 'queued' | 'uploading' | 'transcribing' | 'transcribed' | 'archived' | 'failed' | 'deleted';
interface AudioArtifact {
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
interface StoredAudioArtifact extends AudioArtifact {
    blob: Blob;
}
interface AudioQueuePolicy {
    maxItems: number;
    maxBytes: number;
    maxBytesPerItem: number;
}
declare const AUDIO_QUEUE_DEFAULTS: AudioQueuePolicy;
declare function makeArtifactId(): string;
declare function isPending(a: AudioArtifact): boolean;
declare function isTerminal$1(a: AudioArtifact): boolean;
declare function artifactLabel(state: AudioArtifactState): string;
declare function formatArtifactSize(bytes: number): string;
declare function formatArtifactDuration(ms?: number): string;

interface AudioQueueStoreOptions {
    dbName?: string;
    storeName?: string;
}
declare class AudioQueueStore {
    private readonly dbName;
    private readonly storeName;
    private dbPromise;
    constructor(opts?: AudioQueueStoreOptions);
    private open;
    private run;
    list(): Promise<StoredAudioArtifact[]>;
    get(id: string): Promise<StoredAudioArtifact | null>;
    put(artifact: StoredAudioArtifact): Promise<void>;
    updateMeta(id: string, patch: Partial<Omit<AudioArtifact, 'id' | 'blob'>>): Promise<void>;
    delete(id: string): Promise<void>;
    clear(): Promise<void>;
}

declare function useAudioQueueStore(identityKey: string | null | undefined, options?: Omit<AudioQueueStoreOptions, 'dbName'>): AudioQueueStore;

interface UseDurableRecordingOptions {
    store: AudioQueueStore;
    policy?: AudioQueuePolicy;
    deviceId?: string | null;
    onSaved?: (artifact: AudioArtifact) => void;
    onError?: (message: string) => void;
}
interface UseDurableRecordingReturn {
    artifact: AudioArtifact | null;
    recordingTime: number;
    /** Everything recorded so far, available while state === 'paused' (null
     * otherwise). A complete playable WAV — feed it to a player as a preview. */
    pausedPreviewBlob: Blob | null;
    bands: number[];
    audioLevel: number;
    isSilent: boolean;
    isStarting: boolean;
    startRecording: () => Promise<void>;
    pauseRecording: () => void;
    resumeRecording: () => void;
    stopRecording: () => Promise<AudioArtifact | null>;
    cancelRecording: () => void;
    isAtCapacity: boolean;
}
declare function useDurableRecording(opts: UseDurableRecordingOptions): UseDurableRecordingReturn;

interface UseAudioQueueOptions {
    store: AudioQueueStore;
    adapter?: VoiceAdapter;
    onTranscribed?: (id: string, text: string) => void;
    onError?: (id: string, message: string) => void;
}
interface UseAudioQueueReturn {
    artifacts: AudioArtifact[];
    totalBytes: number;
    isLoading: boolean;
    transcribeArtifact: (id: string) => Promise<void>;
    retryTranscription: (id: string) => Promise<void>;
    getPlaybackUrl: (id: string) => Promise<string | null>;
    deleteArtifact: (id: string) => Promise<void>;
    archiveArtifact: (id: string) => Promise<void>;
    clearTranscribed: () => Promise<void>;
    reload: () => Promise<void>;
}
declare function useAudioQueue(opts: UseAudioQueueOptions): UseAudioQueueReturn;

interface AudioQueuePanelProps {
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
declare function AudioQueuePanel({ queue, className, privacyNotice, privacyNoticeMs, maxVisible, excludeIds, }: AudioQueuePanelProps): react.JSX.Element | null;

interface AudioQueueItemProps {
    artifact: AudioArtifact;
    onTranscribe?: (id: string) => void;
    onRetry?: (id: string) => void;
    onDelete?: (id: string) => void;
    /** Mark a transcribed artifact as used/sent — hides it from the queue
     * without deleting the audio. */
    onArchive?: (id: string) => void;
    onGetPlaybackUrl?: (id: string) => Promise<string | null>;
    className?: string;
}
declare function AudioQueueItem({ artifact, onTranscribe, onRetry, onDelete, onArchive, onGetPlaybackUrl, className, }: AudioQueueItemProps): react.JSX.Element;

interface AudioDraftPlayerProps {
    /** The draft artifact (the just-recorded, not-yet-acted-on audio). */
    artifact: AudioArtifact;
    /** Resolve a playback object URL for the artifact (revoked here on unmount). */
    onGetPlaybackUrl?: (id: string) => Promise<string | null>;
    /** Primary action — transcribe / send / use the draft. */
    onPrimary?: (id: string) => void;
    /** Discard the draft (deletes the real artifact). */
    onDiscard?: (id: string) => void;
    /** Retry a failed primary action. */
    onRetry?: (id: string) => void;
    /** Resume a paused recording. When provided, a Resume button replaces the
     * primary action (the user hasn't finished recording yet). */
    onResume?: () => void;
    /** Everything recorded so far, available while paused (segmented pause).
     * When set, the paused row plays it back through RichAudioPlayer. */
    pausedPreview?: Blob | null;
    /** Label for the primary action button (default: "Transcribir"). */
    primaryActionLabel?: string;
    /**
     * Visual chrome (COMPOSER-FRAME-2):
     *  - `"card"` (default): standalone frosted card — the sibling-card layout
     *    existing consumers render above the composer.
     *  - `"row"`: bare flex row for living INSIDE the composer box (the
     *    ComposerFrame header slot) — no background, border, radius or shadow;
     *    the box already provides the chrome.
     */
    variant?: 'card' | 'row';
    className?: string;
}
declare function AudioDraftPlayer({ artifact, onGetPlaybackUrl, onPrimary, onDiscard, onRetry, onResume, pausedPreview, primaryActionLabel, variant, className, }: AudioDraftPlayerProps): react.JSX.Element;

/**
 * Concatenate same-format PCM WAV blobs into one WAV.
 *
 * A single segment is returned as-is (no parse, no copy) — the common case
 * when the user never paused. Throws if segments disagree on sample rate,
 * channels, or bit depth: that would splice garbage, and the recorder pins
 * one format for the whole session, so a mismatch is a bug upstream.
 */
declare function mergeWavBlobs(blobs: Blob[]): Promise<Blob>;

/**
 * resonanceCallMachine — the headless turn-taking core of RESONANCE, fi-glass's
 * hands-free continuous voice-call mode.
 *
 * A pure (state, event) -> state reducer with zero adapter, React, or transport
 * dependency. The useResonanceCallLoop hook drives it from real TTS/STT adapters;
 * this module only governs which turn-state is legal next. Keeping the machine
 * pure is what makes the four canonical flows — happy path, barge-in, auto-resume,
 * sleep hangup — verifiable without mocking audio I/O.
 *
 * RESONANCE is the voice CHANNEL through which any elemento (persona) speaks; it is
 * not an elemento itself. See .claude/backlog/og118-resonance-voice-mode.md.
 */
type ResonanceCallState = 'idle' | 'listening' | 'transcribing' | 'thinking' | 'speaking' | 'interrupted' | 'silence_hold' | 'sleep_decay' | 'ended';
type ResonanceCallEvent = 'call.started' | 'mic.opened' | 'user.speech.started' | 'user.speech.ended' | 'stt.completed' | 'assistant.speech.started' | 'assistant.speech.interrupted' | 'assistant.speech.completed' | 'silence.detected' | 'silence.resume' | 'sleep.decay.started' | 'error.recoverable' | 'error.fatal' | 'call.ended';
declare const RESONANCE_INITIAL_STATE: ResonanceCallState;
declare function isTerminal(state: ResonanceCallState): boolean;
declare function resonanceCallReducer(state: ResonanceCallState, event: ResonanceCallEvent): ResonanceCallState;

/**
 * resonanceEffects — the pure state-to-effect mapping that bridges the
 * resonanceCallMachine reducer to real TTS/STT/mic adapters.
 *
 * useResonanceCallLoop drives the reducer, then on every state ENTERED asks
 * effectForState which single imperative effect to run, and dispatches it to the
 * injected driver (open the mic, cut TTS on barge-in, invoke the agent, etc.).
 * Keeping the mapping pure means the orchestration contract is verifiable without
 * mocking audio I/O — the driver is the only thing the React hook has to wire.
 */

type ResonanceEffect = {
    type: 'open_mic';
} | {
    type: 'begin_transcribe';
} | {
    type: 'invoke_agent';
} | {
    type: 'speak';
} | {
    type: 'stop_speaking';
} | {
    type: 'hold_silence';
} | {
    type: 'fade_and_hangup';
} | {
    type: 'end_call';
};
/**
 * The single effect to run on entering `state`, or null when the state needs no
 * adapter action (idle). Only fire when the state actually CHANGED — re-entering
 * the same state must not re-dispatch (the hook guards on prev !== next).
 */
declare function effectForState(state: ResonanceCallState): ResonanceEffect | null;
interface ResonanceDriver {
    openMic: () => void;
    beginTranscribe: () => void;
    invokeAgent: () => void;
    speak: () => void;
    stopSpeaking: () => void;
    holdSilence: () => void;
    fadeAndHangup: () => void;
    endCall: () => void;
}
/** Dispatch one effect to the driver. Returns true when an effect ran. */
declare function dispatchEffect(effect: ResonanceEffect | null, driver: ResonanceDriver): boolean;

/**
 * resonanceCallController — the framework-agnostic heart of useResonanceCallLoop.
 *
 * Holds the resonanceCallMachine state, and on every CHANGED state dispatches the
 * single effectForState to the injected ResonanceDriver. External signals (mic
 * opened, end-of-speech silence, STT transcript, assistant text, TTS completed,
 * barge-in) enter through named methods that map to FSM events. No React, no
 * audio I/O — so the full turn-taking contract is verifiable with vitest + a mock
 * driver, exactly as the coagent's contract requires. useResonanceCallLoop is a
 * thin React wrapper that binds the real adapters to this controller.
 */

interface ResonanceControllerHooks {
    onState?: (state: ResonanceCallState) => void;
    onEvent?: (event: ResonanceCallEvent, state: ResonanceCallState) => void;
}
interface ResonanceCallController {
    state: () => ResonanceCallState;
    lastTranscript: () => string | undefined;
    lastAssistantText: () => string | undefined;
    events: () => ResonanceCallEvent[];
    send: (event: ResonanceCallEvent) => ResonanceCallState;
    startCall: () => void;
    micOpened: () => void;
    userSpeechStarted: () => void;
    userSpeechEnded: () => void;
    sttCompleted: (transcript: string) => void;
    assistantTurnReady: (text: string) => void;
    ttsCompleted: () => void;
    ttsInterrupted: () => void;
    silenceDetected: () => void;
    silenceResume: () => void;
    sleepDecay: () => void;
    /** Barge-in helper: cut TTS, then re-open for the user's new turn. */
    interrupt: () => void;
    /** A recoverable adapter failure (STT/agent/TTS) — drop back to listening. */
    failRecoverable: () => void;
    /** A fatal adapter failure (mic lost) — hang up the call. */
    failFatal: () => void;
    endCall: () => void;
}
declare function createResonanceCallController(driver: ResonanceDriver, hooks?: ResonanceControllerHooks): ResonanceCallController;

/**
 * resonanceVadGate — a pure, time-driven voice-activity detector for RESONANCE.
 *
 * The first VAD attempt closed end-of-speech off a React effect watching a
 * derived `isSilent` boolean — it flaked, because re-renders are not a reliable
 * clock and a single threshold has no hysteresis. This gate instead takes the
 * CURRENT audio level + a monotonic timestamp on every tick (the React layer
 * drives it from a setInterval reading an audioLevel ref) and decides with
 * two-threshold hysteresis + minimum durations. No React, no audio I/O — so the
 * timing contract is verifiable with an injected clock + level. audioLevel is the
 * 0-255 analyser average (see useAudioAnalysis).
 */
interface ResonanceVadConfig {
    /** Level (0-255) to DECLARE speech onset — high, to reject noise. */
    speechOnThreshold: number;
    /** Level (0-255) below which counts as silence — low, the hysteresis floor. */
    speechOffThreshold: number;
    /** Sustained-above-on time before emitting speech_start (debounce). */
    minSpeechMs: number;
    /** Sustained-below-off time after last voice before emitting speech_end. */
    endSilenceMs: number;
    /** Hard cap on a single user turn; forces speech_end. */
    maxTurnMs: number;
}
declare const DEFAULT_VAD_CONFIG: ResonanceVadConfig;
/** What the gate is allowed to detect this tick, derived from the call state. */
type ResonanceVadMode = 'detect' | 'barge' | 'idle';
type ResonanceVadEvent = 'speech_start' | 'speech_end' | 'barge_in' | null;
interface ResonanceVadGate {
    /** Feed the current level + monotonic now (ms). Returns one event or null. */
    tick: (level: number, nowMs: number, mode: ResonanceVadMode) => ResonanceVadEvent;
    reset: () => void;
}
declare function createResonanceVadGate(config?: ResonanceVadConfig): ResonanceVadGate;

/**
 * resonanceCueController — applies resonanceCuePolicy decisions to a CuePlayer,
 * with the guarantees Web Audio alone can't give: playLoop is idempotent (one
 * thinking source, never two), playOnce dedupes by eventId (a re-render of the
 * same transition can't double-fire), and stopAll is safe to call any number of
 * times. The controller knows the policy; the player only knows Web Audio.
 *
 * Lifecycle: one controller per call session (startCall makes/reset()s it). On
 * teardown the wrapper calls stopAll() — and the policy also emits stopAll on the
 * terminal transition — so no cue can outlive the call.
 */

interface ResonanceCuePlayer {
    playOnce: (cue: 'crystalline' | 'ready') => void;
    playLoop: (cue: 'thinking') => void;
    stopLoop: (cue: 'thinking') => void;
    stopAll: () => void;
}
interface ResonanceCueController {
    /** Apply one FSM transition's cues. eventId dedupes one-shots across re-renders. */
    applyTransition: (input: {
        previousState: ResonanceCallState;
        nextState: ResonanceCallState;
        event: ResonanceCallEvent;
    }, eventId?: string) => void;
    stopAll: () => void;
    reset: () => void;
}
declare function createResonanceCueController(player: ResonanceCuePlayer): ResonanceCueController;

/**
 * createAudioCuePlayer — the thin Web Audio adapter behind resonanceCueController.
 *
 * Pre-decodes the three cue buffers and plays them with the low latency only the
 * Web Audio API gives (AudioBufferSourceNode, not <audio>). It knows nothing about
 * the FSM — it just plays, loops, and stops. stopLoop/stopAll are best-effort so a
 * teardown never throws, and one-shots self-evict on ended so they can overlap
 * without leaking nodes.
 */

interface AudioCueAssets {
    thinking: string;
    crystalline: string;
    ready: string;
}
interface AudioCuePlayerOptions {
    volume?: number;
}
interface AudioCuePlayer extends ResonanceCuePlayer {
    preload: () => Promise<void>;
    /** Resume the AudioContext from a user gesture (the call button). Returns the state. */
    resume: () => Promise<string>;
    dispose: () => void;
}
declare function createAudioCuePlayer(assets: AudioCueAssets, options?: AudioCuePlayerOptions): AudioCuePlayer;

interface ResonanceCallAdapters {
    /** Open the mic stream (useDurableRecording.startRecording). */
    openMic: () => void | Promise<void>;
    /** Close the mic stream (useDurableRecording.stopRecording). */
    closeMic: () => void | Promise<void>;
    /** Stop the current segment and push it to STT; resolve with transcript text. */
    beginTranscribe: () => Promise<string>;
    /** Run the agent over the (already-appended) client-sent history; resolve with assistant text. */
    invokeAgent: () => Promise<string>;
    /** Synthesize + play the assistant text (useVoice.generateAudio + playback). */
    speak: (text: string) => void | Promise<void>;
    /** Cut TTS playback immediately (useVoice.close) — barge-in. */
    stopSpeaking: () => void;
    /** Append the user transcript to the client-sent history before invokeAgent. */
    appendUserMessage: (text: string) => void;
}
interface ResonanceSilencePolicy {
    endOfSpeechMs: number;
    autoResumeMs: number;
}
interface ResonanceSleepPolicy {
    enabled: boolean;
    idleHangupMs: number;
}
interface ResonanceBargeInPolicy {
    enabled: boolean;
}
interface UseResonanceCallLoopParams {
    enabled: boolean;
    adapters: ResonanceCallAdapters;
    /**
     * Read the CURRENT input level (0-255 analyser average). Polled on a stable
     * 50ms timer by the robust VAD gate — not a re-render-driven boolean, which
     * was the source of the frozen-loop flakiness.
     */
    getAudioLevel: () => number;
    /** Hysteresis + timing thresholds for the VAD gate. */
    vadConfig?: ResonanceVadConfig;
    silencePolicy?: ResonanceSilencePolicy;
    sleepPolicy?: ResonanceSleepPolicy;
    bargeInPolicy?: ResonanceBargeInPolicy;
    /** Audio cues (thinking loop / crystalline / ready). Off unless enabled + assets given. */
    audioCues?: {
        enabled: boolean;
        assets: AudioCueAssets;
        volume?: number;
    };
    /** Expose window.__RESONANCE_EVENTS__ for the screenless E2E harness. */
    debug?: boolean;
    onEvent?: (event: ResonanceCallEvent, state: ResonanceCallState) => void;
}
interface UseResonanceCallLoopReturn {
    state: ResonanceCallState;
    isActive: boolean;
    isListening: boolean;
    isSpeaking: boolean;
    isThinking: boolean;
    lastTranscript?: string;
    lastAssistantText?: string;
    startCall: () => Promise<void>;
    endCall: () => void;
    interrupt: () => void;
}
interface ResonanceEventRecord {
    type: ResonanceCallEvent | 'stt.completed' | 'assistant.text';
    state: ResonanceCallState;
    transcript?: string;
    text?: string;
    timestamp: number;
}
declare global {
    interface Window {
        __RESONANCE_EVENTS__?: ResonanceEventRecord[];
    }
}
declare function useResonanceCallLoop(params: UseResonanceCallLoopParams): UseResonanceCallLoopReturn;

/**
 * resonanceCuePolicy — the pure decision layer for RESONANCE's audio cues.
 *
 * Maps a single FSM transition (previousState, nextState, event) to the cue
 * actions to run. No Web Audio, no timers — so "right cue only on its transition"
 * and "the thinking loop can never hang" are provable with plain assertions.
 *
 * The load-bearing rule: stopLoop(thinking) is derived from LEAVING the thinking
 * state, not from a specific event. That makes it impossible to strand the loop —
 * a barge-in, an agent error, a hangup, or any future transition out of thinking
 * all stop it. stopAll is layered on top for terminal/teardown paths.
 */

type ResonanceCueName = 'thinking' | 'crystalline' | 'ready';
type ResonanceCueAction = {
    type: 'playLoop';
    cue: 'thinking';
} | {
    type: 'stopLoop';
    cue: 'thinking';
} | {
    type: 'playOnce';
    cue: 'crystalline' | 'ready';
} | {
    type: 'stopAll';
};
interface ResonanceCuePolicyInput {
    previousState: ResonanceCallState;
    nextState: ResonanceCallState;
    event: ResonanceCallEvent;
}
declare function resonanceCuePolicy(input: ResonanceCuePolicyInput): ResonanceCueAction[];

export { AUDIO_QUEUE_DEFAULTS, type AudioArtifact, type AudioArtifactState, type AudioCueAssets, type AudioCuePlayer, type AudioCuePlayerOptions, AudioDraftPlayer, type AudioDraftPlayerProps, type AudioElementLike, AudioPlayer, type AudioPlayerController, type AudioPlayerOptions, type AudioPlayerProps, type AudioPlayerState, type AudioPlayerStatus, AudioQueueItem, type AudioQueueItemProps, AudioQueuePanel, type AudioQueuePanelProps, type AudioQueuePolicy, AudioQueueStore, type AudioQueueStoreOptions, AudioVisualizer, type AudioVisualizerProps, type AudioVisualizerVariant, BUTTON_SIZES, type ButtonSize, type ButtonSizeConfig, COLOR_THEMES, type ColorTheme, ComposerMicSlot, type ComposerMicSlotProps, DEFAULT_VAD_CONFIG, type PulseConfig, PulseRings, type PulseRingsProps, type PulseStyle, RESONANCE_INITIAL_STATE, RecordingButton, type RecordingButtonProps, type RecordingStateType, RecordingTimer, type RecordingTimerProps, type ResonanceBargeInPolicy, type ResonanceCallAdapters, type ResonanceCallController, type ResonanceCallEvent, type ResonanceCallState, type ResonanceControllerHooks, type ResonanceCueAction, type ResonanceCueController, type ResonanceCueName, type ResonanceCuePlayer, type ResonanceCuePolicyInput, type ResonanceDriver, type ResonanceEffect, type ResonanceSilencePolicy, type ResonanceSleepPolicy, type ResonanceVadConfig, type ResonanceVadEvent, type ResonanceVadGate, type ResonanceVadMode, RichAudioPlayer, type RichAudioPlayerProps, STATUS_TEXT_EN, STATUS_TEXT_ES, SpeakButton, type SpeakButtonProps, type StateColors, StatusText, type StatusTextConfig, type StatusTextProps, type StoredAudioArtifact, type UseAudioPlayerOptions, type UseAudioPlayerReturn, type UseAudioQueueOptions, type UseAudioQueueReturn, type UseDictationOptions, type UseDictationReturn, type UseDurableRecordingOptions, type UseDurableRecordingReturn, type UseResonanceCallLoopParams, type UseResonanceCallLoopReturn, type UseVoiceOptions, type UseVoiceReturn, VoiceMicButton, artifactLabel, createAudioCuePlayer, createAudioPlayer, createResonanceCallController, createResonanceCueController, createResonanceVadGate, dispatchEffect, effectForState, formatArtifactDuration, formatArtifactSize, formatPlaybackTime, formatRecordingTime, isPending, isTerminal as isResonanceTerminal, isTerminal$1 as isTerminal, makeArtifactId, makeRecorder, mergeWavBlobs, normalizeLevels, resampleLevels, resonanceCallReducer, resonanceCuePolicy, useAudioAnalysis, useAudioPlayer, useAudioQueue, useAudioQueueStore, useDictation, useDurableRecording, useRecorder, useResonanceCallLoop, useVoice };
