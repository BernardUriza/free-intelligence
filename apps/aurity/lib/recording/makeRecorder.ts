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

export type ChunkHandler = (blob: Blob) => void;

export interface RecorderOptions {
  timeSlice?: number;      // Chunk duration in ms (default: 3000)
  sampleRate?: number;     // Desired sample rate (default: 16000)
  channels?: number;       // Audio channels (default: 1 = mono)
}

export interface Recorder {
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
export async function makeRecorder(
  stream: MediaStream,
  onChunk: ChunkHandler,
  opts?: RecorderOptions
): Promise<Recorder> {
  const timeSlice = opts?.timeSlice;
  const channels = opts?.channels ?? 1;

  // Dynamic import for code splitting + SSR safety
  const mod: any = await import('recordrtc');
  const RecordRTC = mod.default ?? mod;

  if (!RecordRTC) {
    throw new Error('[makeRecorder] RecordRTC library not available');
  }

  // Select best MIME type (WAV is most compatible with all STT providers)
  const mimeType = 'audio/wav';

  let currentRecorder: any = null;
  let loopTimer: NodeJS.Timeout | null = null;
  let isActive = false;

  const createRecorder = () => {
    return new RecordRTC(stream, {
      type: 'audio',
      recorderType: RecordRTC.StereoAudioRecorder,
      mimeType,
      numberOfAudioChannels: channels,
      desiredSampRate: opts?.sampleRate ?? 16000,
      disableLogs: true,
    });
  };

  const startLoop = async () => {
    if (!isActive) return;

    currentRecorder = createRecorder();
    currentRecorder.startRecording();

    // Only schedule loop if timeSlice is provided
    if (timeSlice && timeSlice > 0) {
      loopTimer = setTimeout(async () => {
        if (!currentRecorder || !isActive) return;

        currentRecorder.stopRecording(() => {
          if (!isActive) return;

          const blob = currentRecorder.getBlob();

          if (blob && blob.size > 0) {
            onChunk(blob);
          }

          if (isActive) {
            startLoop();
          }
        });
      }, timeSlice);
    }
  };

  return {
    start: () => {
      isActive = true;
      startLoop();
    },
    stop: () =>
      new Promise<Blob>((resolve) => {
        isActive = false;

        if (loopTimer) {
          clearTimeout(loopTimer);
          loopTimer = null;
        }

        if (currentRecorder) {
          currentRecorder.stopRecording(() => {
            const finalBlob = currentRecorder.getBlob();
            resolve(finalBlob);
          });
        } else {
          resolve(new Blob([], { type: mimeType }));
        }
      }),
    kind: 'recordrtc' as const,
  };
}

/**
 * Guess file extension from MIME type.
 */
export function guessExt(mime?: string): string {
  const m = (mime || '').split(';')[0].trim();
  if (m === 'audio/webm') return '.webm';
  if (m === 'audio/mp4' || m === 'audio/mp4a-latm') return '.mp4';
  if (m === 'audio/wav' || m === 'audio/wave') return '.wav';
  return '.bin';
}
