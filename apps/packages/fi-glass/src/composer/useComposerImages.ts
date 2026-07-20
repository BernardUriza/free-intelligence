'use client';

/**
 * fi-glass · useComposerImages — image-attachment state for a chat composer
 * (OG118-IMAGE-UPLOAD-1, ChatGPT parity: attach / paste an image, preview it
 * as a chip, send it with the message).
 *
 * Framework-first (DD-002-LESSON): picking, validating, downscaling and
 * base64-encoding an image is a reusable conversation capability, so it lives
 * here — the consumer only flips the surface's `imageAttachments` switch. The
 * hook is transport-free: it produces `MessageImage`s ({mediaType, data}); the
 * app's AgentHook decides how they travel.
 *
 * Size discipline: attached images persist base64-inline in the conversation
 * record, so big camera photos are DOWNSCALED client-side (canvas, max side
 * 2048px, JPEG) before encoding. Small files pass through unchanged (a PNG
 * screenshot keeps its type/transparency). Anything that still exceeds the
 * hard cap after downscaling is rejected loudly via `onError`.
 */

import { useCallback, useRef, useState } from 'react';
import type { MessageImage } from '@free-intelligence/core';

/** Media types the pipeline accepts end-to-end (mirrors the server allowlist). */
export const COMPOSER_IMAGE_MEDIA_TYPES = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
] as const;

/** Picker filter string for the file input. */
export const COMPOSER_IMAGE_ACCEPT = COMPOSER_IMAGE_MEDIA_TYPES.join(',');

/** Default maximum images per message (mirrors the server cap). */
export const DEFAULT_MAX_IMAGES = 4;

/** Files at or under this size are encoded as-is (no canvas round-trip). */
const PASSTHROUGH_BYTES = 1_500_000;
/** Longest side after a downscale. */
const MAX_SIDE_PX = 2048;
const JPEG_QUALITY = 0.85;
/** Hard cap on the encoded base64 payload of ONE image (~3 MB decoded). */
const MAX_ENCODED_CHARS = 4 * 1024 * 1024;

/** One attached image, preview-ready (`dataUrl`) and wire-ready (`data`). */
export interface ComposerImageDraft extends MessageImage {
  /** Stable id for chip rendering/removal. */
  id: string;
  /** `data:<mediaType>;base64,<data>` — feed straight into an <img src>. */
  dataUrl: string;
  /** Original file name (chip title/alt). */
  name: string;
}

export interface UseComposerImagesOptions {
  /** Max images attachable to one message. Default {@link DEFAULT_MAX_IMAGES}. */
  maxImages?: number;
  /** Surfaced with a human-readable message when a file is rejected. */
  onError?: (message: string) => void;
}

export interface ComposerImages {
  /** The images currently attached to the message being composed. */
  drafts: ComposerImageDraft[];
  /** Validate + encode picked/dropped/pasted files into drafts. */
  addFiles: (files: Iterable<File>) => Promise<void>;
  /** Detach one image. */
  remove: (id: string) => void;
  /** Detach all (called by the surface after a send). */
  clear: () => void;
  /**
   * Re-attach images handed back by a FAILED turn (`conversation.unsentImages`).
   * A send clears the drafts optimistically, so without this the pictures of a
   * turn the watchdog killed exist nowhere — the user gets their text back and
   * silently re-sends without them. Already-encoded, so no validation/downscale
   * round-trip; still bounded by `maxImages`.
   */
  restore: (images: MessageImage[]) => void;
  /** The drafts as wire-ready MessageImages. */
  toMessageImages: () => MessageImage[];
  /** Extract + add image files from a paste event. True if any were taken. */
  handlePaste: (event: { clipboardData: DataTransfer | null }) => boolean;
}

function readAsDataUrl(file: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error('read failed'));
    reader.readAsDataURL(file);
  });
}

function splitDataUrl(dataUrl: string): { mediaType: string; data: string } | null {
  const match = /^data:([^;,]+);base64,(.+)$/.exec(dataUrl);
  return match ? { mediaType: match[1], data: match[2] } : null;
}

/**
 * Downscale via canvas to {@link MAX_SIDE_PX} and re-encode as JPEG. Returns
 * null when the environment lacks the drawing APIs (SSR, jsdom) — the caller
 * then rejects the file instead of sending an oversized payload.
 */
async function downscale(file: File): Promise<string | null> {
  if (typeof document === 'undefined' || typeof createImageBitmap !== 'function') return null;
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    return null;
  }
  try {
    const scale = Math.min(1, MAX_SIDE_PX / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    // Downscaled output is JPEG: transparency flattens onto white instead of
    // black (the canvas default for JPEG's missing alpha channel).
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg', JPEG_QUALITY);
  } finally {
    bitmap.close();
  }
}

let nextDraftId = 0;

export function useComposerImages(options: UseComposerImagesOptions = {}): ComposerImages {
  const { maxImages = DEFAULT_MAX_IMAGES, onError } = options;
  const [drafts, setDrafts] = useState<ComposerImageDraft[]>([]);
  // Read inside async addFiles without stale closures.
  const draftsRef = useRef(drafts);
  draftsRef.current = drafts;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  const addFiles = useCallback(
    async (files: Iterable<File>) => {
      // Count locally: setDrafts is async, so the ref alone would let one big
      // batch blow past the cap (each file seeing the pre-batch length).
      let count = draftsRef.current.length;
      for (const file of files) {
        if (!(COMPOSER_IMAGE_MEDIA_TYPES as readonly string[]).includes(file.type)) {
          onErrorRef.current?.(
            'Solo imágenes JPEG, PNG, WebP o GIF.',
          );
          continue;
        }
        if (count >= maxImages) {
          onErrorRef.current?.(`Máximo ${maxImages} imágenes por mensaje.`);
          return;
        }
        let dataUrl: string;
        try {
          if (file.size <= PASSTHROUGH_BYTES) {
            dataUrl = await readAsDataUrl(file);
          } else {
            const scaled = await downscale(file);
            if (!scaled) {
              onErrorRef.current?.(
                `La imagen "${file.name}" es muy grande y no se pudo reducir aquí. Usa una más pequeña.`,
              );
              continue;
            }
            dataUrl = scaled;
          }
        } catch {
          onErrorRef.current?.(`No se pudo leer la imagen "${file.name}".`);
          continue;
        }
        const parts = splitDataUrl(dataUrl);
        if (!parts || parts.data.length > MAX_ENCODED_CHARS) {
          onErrorRef.current?.(
            `La imagen "${file.name}" sigue siendo muy pesada después de reducirla.`,
          );
          continue;
        }
        const draft: ComposerImageDraft = {
          id: `img-${++nextDraftId}`,
          mediaType: parts.mediaType,
          data: parts.data,
          dataUrl,
          name: file.name || 'imagen',
        };
        count += 1;
        setDrafts((prev) => (prev.length >= maxImages ? prev : [...prev, draft]));
      }
    },
    [maxImages],
  );

  const remove = useCallback((id: string) => {
    setDrafts((prev) => prev.filter((d) => d.id !== id));
  }, []);

  const clear = useCallback(() => setDrafts([]), []);

  const restore = useCallback(
    (images: MessageImage[]) => {
      setDrafts(
        images.slice(0, maxImages).map((image) => ({
          id: `img-${++nextDraftId}`,
          mediaType: image.mediaType,
          data: image.data,
          dataUrl: `data:${image.mediaType};base64,${image.data}`,
          name: 'imagen',
        })),
      );
    },
    [maxImages],
  );

  const toMessageImages = useCallback(
    () => draftsRef.current.map((d) => ({ mediaType: d.mediaType, data: d.data })),
    [],
  );

  const handlePaste = useCallback(
    (event: { clipboardData: DataTransfer | null }): boolean => {
      const items = event.clipboardData?.items;
      if (!items) return false;
      const files: File[] = [];
      for (const item of Array.from(items)) {
        if (item.kind === 'file' && item.type.startsWith('image/')) {
          const file = item.getAsFile();
          if (file) files.push(file);
        }
      }
      if (files.length === 0) return false;
      void addFiles(files);
      return true;
    },
    [addFiles],
  );

  return { drafts, addFiles, remove, clear, restore, toMessageImages, handlePaste };
}
