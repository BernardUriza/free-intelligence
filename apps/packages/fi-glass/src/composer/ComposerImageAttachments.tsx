'use client';

/**
 * fi-glass · composer image-attachment UI (OG118-IMAGE-UPLOAD-1):
 *
 *   - ComposerImageChips — thumbnail chips of the images attached to the
 *     message being composed (ComposerFrame HEADER slot: a preview OF the
 *     draft, exactly like the recorded-audio draft), each with a remove button.
 *   - AttachImageButton — the picker trigger (ComposerFrame FOOTER-START rail:
 *     something the user sets before composing, per COMPOSER-FOOTER-ZONES-1).
 *
 * Presentation only — state lives in `useComposerImages`. Styling arrives via
 * className props; sensible inline defaults keep an unstyled consumer usable.
 */

import { useRef } from 'react';
import { ImagePlus, X } from 'lucide-react';
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

export interface AttachImageButtonProps {
  /** Called with the picked files (hand them to `useComposerImages.addFiles`). */
  onFiles: (files: File[]) => void;
  /** Disable the trigger (composer disabled / attachment cap reached). */
  disabled?: boolean;
  className?: string;
  iconClassName?: string;
  /** aria-label. Default: "Adjuntar imagen". */
  label?: string;
}

export function AttachImageButton({
  onFiles,
  disabled = false,
  className,
  iconClassName,
  label = 'Adjuntar imagen',
}: AttachImageButtonProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={COMPOSER_IMAGE_ACCEPT}
        multiple
        style={{ display: 'none' }}
        // Clearing value lets the same file be re-picked after removal.
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          e.target.value = '';
          if (files.length > 0) onFiles(files);
        }}
      />
      <button
        type="button"
        aria-label={label}
        title={label}
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className={`fi-touch-target ${className ?? ''}`.trim()}
        data-fi-attach-image=""
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'transparent',
          border: 'none',
          cursor: disabled ? 'default' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          padding: '0.375rem',
          color: 'inherit',
        }}
      >
        <ImagePlus size={18} aria-hidden className={iconClassName} />
      </button>
    </>
  );
}
