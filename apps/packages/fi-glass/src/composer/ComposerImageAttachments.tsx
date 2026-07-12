'use client';

/**
 * fi-glass · composer image-attachment UI (OG118-IMAGE-UPLOAD-1):
 *
 *   - ComposerImageChips — thumbnail chips of the images attached to the
 *     message being composed (ComposerFrame HEADER slot: a preview OF the
 *     draft, exactly like the recorded-audio draft), each with a remove button.
 *   - useImagePicker — the hidden file input + an `open()` to trigger it. Not a
 *     button: attaching an image is ONE of the composer's capabilities, and they
 *     all live behind the shared "+" (ComposerActions). A dedicated icon button
 *     per capability is exactly the crowding the "+" exists to prevent.
 *
 * Presentation only — state lives in `useComposerImages`. Styling arrives via
 * className props; sensible inline defaults keep an unstyled consumer usable.
 */

import { useRef, type ReactNode } from 'react';
import { X } from 'lucide-react';
import type { ComposerImageDraft } from './useComposerImages';
import { COMPOSER_IMAGE_ACCEPT } from './useComposerImages';

export interface ComposerImageChipsProps {
  drafts: ComposerImageDraft[];
  onRemove: (id: string) => void;
  /** Disable removal (e.g. while a turn streams). */
  disabled?: boolean;
  className?: string;
  /** aria-label template for a chip's remove button. Default: "Quitar imagen". */
  removeLabel?: string;
}

export function ComposerImageChips({
  drafts,
  onRemove,
  disabled = false,
  className,
  removeLabel = 'Quitar imagen',
}: ComposerImageChipsProps) {
  if (drafts.length === 0) return null;
  return (
    <div
      className={className}
      data-fi-image-chips=""
      style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}
    >
      {drafts.map((draft) => (
        <div key={draft.id} style={{ position: 'relative' }}>
          <img
            src={draft.dataUrl}
            alt={draft.name}
            title={draft.name}
            style={{
              width: '3.5rem',
              height: '3.5rem',
              objectFit: 'cover',
              borderRadius: '0.5rem',
              display: 'block',
            }}
          />
          <button
            type="button"
            aria-label={`${removeLabel}: ${draft.name}`}
            onClick={() => onRemove(draft.id)}
            disabled={disabled}
            style={{
              position: 'absolute',
              top: '-0.375rem',
              right: '-0.375rem',
              width: '1.25rem',
              height: '1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '9999px',
              border: 'none',
              cursor: disabled ? 'default' : 'pointer',
              background: 'rgba(0,0,0,0.65)',
              color: '#fff',
              padding: 0,
            }}
          >
            <X size={12} aria-hidden />
          </button>
        </div>
      ))}
    </div>
  );
}

export interface ImagePicker {
  /** Render this anywhere inside the composer — it is the hidden file input. */
  input: ReactNode;
  /** Open the OS file picker (wire it to a ComposerAction's onSelect). */
  open: () => void;
}

/**
 * The image file-picker as a CAPABILITY, not a button: it hands back the hidden
 * input to render and an `open()` for whatever affordance invokes it — today the
 * shared "+" menu (ComposerActions).
 */
export function useImagePicker(onFiles: (files: File[]) => void): ImagePicker {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const input = (
    <input
      ref={inputRef}
      type="file"
      accept={COMPOSER_IMAGE_ACCEPT}
      multiple
      style={{ display: 'none' }}
      data-fi-image-input=""
      // Clearing value lets the same file be re-picked after removal.
      onChange={(e) => {
        const files = Array.from(e.target.files ?? []);
        e.target.value = '';
        if (files.length > 0) onFiles(files);
      }}
    />
  );
  return { input, open: () => inputRef.current?.click() };
}
