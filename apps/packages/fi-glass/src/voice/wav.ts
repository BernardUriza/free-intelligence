// B3-VOICE-FIGLASS-18 — WAV segment concatenation.
//
// Segmented pause: pausing a recording stops the live RecordRTC instance (the
// only way it yields a blob) and keeps the WAV as a SEGMENT; resuming starts a
// fresh recorder on the same stream. This module merges those segments back
// into one playable/transcribable WAV. It exists because RecordRTC cannot hand
// out a partial blob mid-recording — but a stopped segment IS a complete WAV,
// and same-format PCM WAVs concatenate exactly (strip headers, splice data,
// rewrite one header). This is why the recorder pins audio/wav over webm:
// webm clusters cannot be spliced this way.

interface WavInfo {
  /** fmt chunk fields needed to rewrite a canonical header. */
  audioFormat: number;
  numChannels: number;
  sampleRate: number;
  bitsPerSample: number;
  /** Raw PCM payload (the 'data' chunk body). */
  data: Uint8Array;
}

// Blob.arrayBuffer() is baseline in browsers but absent in jsdom — fall back
// to FileReader so the splice stays unit-testable.
function blobToArrayBuffer(blob: Blob): Promise<ArrayBuffer> {
  if (typeof blob.arrayBuffer === 'function') return blob.arrayBuffer();
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(reader.error ?? new Error('FileReader failed'));
    reader.readAsArrayBuffer(blob);
  });
}

function readFourCC(view: DataView, offset: number): string {
  return String.fromCharCode(
    view.getUint8(offset),
    view.getUint8(offset + 1),
    view.getUint8(offset + 2),
    view.getUint8(offset + 3),
  );
}

/** Parse a RIFF/WAVE buffer: walk chunks for 'fmt ' and 'data'. */
function parseWav(buffer: ArrayBuffer): WavInfo {
  const view = new DataView(buffer);
  if (buffer.byteLength < 44 || readFourCC(view, 0) !== 'RIFF' || readFourCC(view, 8) !== 'WAVE') {
    throw new Error('Not a RIFF/WAVE file');
  }

  let fmt: Omit<WavInfo, 'data'> | null = null;
  let data: Uint8Array | null = null;
  let offset = 12;
  while (offset + 8 <= buffer.byteLength) {
    const id = readFourCC(view, offset);
    const size = view.getUint32(offset + 4, true);
    const body = offset + 8;
    if (id === 'fmt ') {
      fmt = {
        audioFormat: view.getUint16(body, true),
        numChannels: view.getUint16(body + 2, true),
        sampleRate: view.getUint32(body + 4, true),
        bitsPerSample: view.getUint16(body + 14, true),
      };
    } else if (id === 'data') {
      const end = Math.min(body + size, buffer.byteLength);
      data = new Uint8Array(buffer.slice(body, end));
    }
    // Chunks are word-aligned: odd sizes carry a pad byte.
    offset = body + size + (size % 2);
  }

  if (!fmt || !data) throw new Error('WAV missing fmt or data chunk');
  return { ...fmt, data };
}

/** Build a canonical 44-byte-header PCM WAV from format info + PCM payload. */
function buildWav(fmt: Omit<WavInfo, 'data'>, pcm: Uint8Array): Blob {
  const header = new ArrayBuffer(44);
  const view = new DataView(header);
  const byteRate = (fmt.sampleRate * fmt.numChannels * fmt.bitsPerSample) / 8;
  const blockAlign = (fmt.numChannels * fmt.bitsPerSample) / 8;

  const writeFourCC = (offset: number, s: string) => {
    for (let i = 0; i < 4; i++) view.setUint8(offset + i, s.charCodeAt(i));
  };
  writeFourCC(0, 'RIFF');
  view.setUint32(4, 36 + pcm.byteLength, true);
  writeFourCC(8, 'WAVE');
  writeFourCC(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, fmt.audioFormat, true);
  view.setUint16(22, fmt.numChannels, true);
  view.setUint32(24, fmt.sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, fmt.bitsPerSample, true);
  writeFourCC(36, 'data');
  view.setUint32(40, pcm.byteLength, true);

  return new Blob([header, pcm.buffer as ArrayBuffer], { type: 'audio/wav' });
}

/**
 * Concatenate same-format PCM WAV blobs into one WAV.
 *
 * A single segment is returned as-is (no parse, no copy) — the common case
 * when the user never paused. Throws if segments disagree on sample rate,
 * channels, or bit depth: that would splice garbage, and the recorder pins
 * one format for the whole session, so a mismatch is a bug upstream.
 */
export async function mergeWavBlobs(blobs: Blob[]): Promise<Blob> {
  if (blobs.length === 0) throw new Error('No WAV segments to merge');
  if (blobs.length === 1) return blobs[0];

  const parsed = await Promise.all(
    blobs.map(async (b) => parseWav(await blobToArrayBuffer(b))),
  );

  const first = parsed[0];
  for (const p of parsed.slice(1)) {
    if (
      p.audioFormat !== first.audioFormat ||
      p.numChannels !== first.numChannels ||
      p.sampleRate !== first.sampleRate ||
      p.bitsPerSample !== first.bitsPerSample
    ) {
      throw new Error('WAV segments have mismatched formats');
    }
  }

  const total = parsed.reduce((s, p) => s + p.data.byteLength, 0);
  const pcm = new Uint8Array(total);
  let cursor = 0;
  for (const p of parsed) {
    pcm.set(p.data, cursor);
    cursor += p.data.byteLength;
  }

  return buildWav(first, pcm);
}
