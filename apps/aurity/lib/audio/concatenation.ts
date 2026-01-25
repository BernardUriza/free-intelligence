/**
 * Audio Concatenation Utilities
 *
 * Extracted from ConversationCapture during refactoring.
 * Handles audio blob concatenation for multi-segment recordings.
 */

export interface ConcatenationResult {
  blob: Blob;
  sizeMB: number;
  segmentCount: number;
  mimeType: string;
}

/**
 * Concatenate multiple audio blobs into a single blob
 */
export function concatenateAudioBlobs(blobs: Blob[]): ConcatenationResult | null {
  if (blobs.length === 0) return null;

  // Determine MIME type from first blob
  const mimeType = blobs[0].type || 'audio/webm';

  // Concatenate all blobs
  const concatenatedBlob = new Blob(blobs, { type: mimeType });

  const sizeMB = concatenatedBlob.size / 1024 / 1024;

  console.log(
    `[AudioConcat] [OK] Concatenated ${blobs.length} segments: ${sizeMB.toFixed(2)} MB`
  );

  return {
    blob: concatenatedBlob,
    sizeMB,
    segmentCount: blobs.length,
    mimeType,
  };
}

/**
 * Clean up an object URL safely
 */
export function revokeAudioUrl(url: string | null): void {
  if (url) {
    URL.revokeObjectURL(url);
    console.log('[AudioConcat] Cleaned up audio URL');
  }
}
