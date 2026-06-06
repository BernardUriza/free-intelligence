import * as react from 'react';
import { LucideIcon } from 'lucide-react';
import { VoiceAdapter } from '@free-intelligence/core';

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
    /** Size preset (drives default padding + icon size). */
    size?: 'xs' | 'sm' | 'md';
    /** Override the button class entirely (e.g. aurity's exact legacy string). */
    className?: string;
    /** Override the icon class. */
    iconClassName?: string;
    /** Override the tooltip (default: "Escuchar (<voice>)"). */
    title?: string;
}
declare function SpeakButton({ content, voice, isUserMessage, onOpenPlayer, size, className, iconClassName, title, }: SpeakButtonProps): react.JSX.Element;

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
}
interface UseAudioAnalysisReturn {
    audioLevel: number;
    isSilent: boolean;
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

export { BUTTON_SIZES, type ButtonSize, type ButtonSizeConfig, COLOR_THEMES, type ColorTheme, type PulseConfig, PulseRings, type PulseRingsProps, type PulseStyle, RecordingButton, type RecordingButtonProps, type RecordingStateType, RecordingTimer, type RecordingTimerProps, STATUS_TEXT_EN, STATUS_TEXT_ES, SpeakButton, type SpeakButtonProps, type StateColors, StatusText, type StatusTextConfig, type StatusTextProps, type UseDictationOptions, type UseDictationReturn, type UseVoiceOptions, type UseVoiceReturn, VoiceMicButton, formatRecordingTime, makeRecorder, useAudioAnalysis, useDictation, useRecorder, useVoice };
