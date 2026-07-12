'use client';

/**
 * fi-glass · MessageImages — the images attached to a chat message, rendered
 * in its bubble (OG118-IMAGE-UPLOAD-1). Framework-owned so every shell's
 * transcript shows the picture the user sent (live-optimistic AND after a
 * reload — the base64 rides inside the persisted ChatMessage).
 */

import type { MessageImage } from '@free-intelligence/core';

export interface MessageImagesProps {
  images: MessageImage[] | undefined;
  className?: string;
  imageClassName?: string;
  /** alt-text prefix per image. Default: "Imagen adjunta". */
  altLabel?: string;
}

export function MessageImages({
  images,
  className,
  imageClassName,
  altLabel = 'Imagen adjunta',
}: MessageImagesProps) {
  if (!images || images.length === 0) return null;
  return (
    <div
      className={className}
      data-fi-message-images=""
      style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}
    >
      {images.map((img, i) => (
        <img
          key={i}
          src={`data:${img.mediaType};base64,${img.data}`}
          alt={`${altLabel} ${i + 1}`}
          loading="lazy"
          style={{
            maxWidth: 'min(100%, 20rem)',
            maxHeight: '20rem',
            borderRadius: '0.75rem',
            display: 'block',
            objectFit: 'contain',
          }}
          className={imageClassName}
        />
      ))}
    </div>
  );
}
