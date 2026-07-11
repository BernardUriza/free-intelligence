// @vitest-environment jsdom
/**
 * Tests for useComposerImages (OG118-IMAGE-UPLOAD-1) — the composer's
 * image-attachment state: validate + encode picked files into wire-ready
 * drafts, cap the count, extract pasted image files, and reject junk loudly
 * via onError (never silently).
 *
 * jsdom has FileReader but no canvas, so these cover the pass-through path
 * (small files) and the rejection paths; the canvas downscale is guarded by
 * feature checks and falls back to a loud rejection, which IS the pinned
 * behavior for an environment without drawing APIs.
 */

import { describe, it, expect, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useComposerImages } from './useComposerImages';

const PNG_BYTES = Uint8Array.from([0x89, 0x50, 0x4e, 0x47]);

function pngFile(name = 'foto.png'): File {
  return new File([PNG_BYTES], name, { type: 'image/png' });
}

describe('useComposerImages', () => {
  it('encodes a small image into a wire-ready draft (base64 + preview dataUrl)', async () => {
    const { result } = renderHook(() => useComposerImages());
    await act(() => result.current.addFiles([pngFile()]));
    await waitFor(() => expect(result.current.drafts).toHaveLength(1));
    const draft = result.current.drafts[0];
    expect(draft.mediaType).toBe('image/png');
    expect(draft.name).toBe('foto.png');
    expect(draft.dataUrl).toBe(`data:image/png;base64,${draft.data}`);
    // The base64 round-trips to the original bytes.
    expect(Uint8Array.from(atob(draft.data), (c) => c.charCodeAt(0))).toEqual(PNG_BYTES);
    expect(result.current.toMessageImages()).toEqual([
      { mediaType: 'image/png', data: draft.data },
    ]);
  });

  it('rejects non-image files with a human-readable error', async () => {
    const onError = vi.fn();
    const { result } = renderHook(() => useComposerImages({ onError }));
    await act(() =>
      result.current.addFiles([new File(['hola'], 'nota.txt', { type: 'text/plain' })]),
    );
    expect(result.current.drafts).toHaveLength(0);
    expect(onError).toHaveBeenCalledWith(expect.stringContaining('JPEG'));
  });

  it('caps the number of attached images and surfaces the limit', async () => {
    const onError = vi.fn();
    const { result } = renderHook(() => useComposerImages({ maxImages: 2, onError }));
    await act(() => result.current.addFiles([pngFile('1.png'), pngFile('2.png'), pngFile('3.png')]));
    await waitFor(() => expect(result.current.drafts).toHaveLength(2));
    expect(onError).toHaveBeenCalledWith(expect.stringContaining('2'));
  });

  it('remove() detaches one draft; clear() detaches all', async () => {
    const { result } = renderHook(() => useComposerImages());
    await act(() => result.current.addFiles([pngFile('a.png'), pngFile('b.png')]));
    await waitFor(() => expect(result.current.drafts).toHaveLength(2));
    act(() => result.current.remove(result.current.drafts[0].id));
    expect(result.current.drafts.map((d) => d.name)).toEqual(['b.png']);
    act(() => result.current.clear());
    expect(result.current.drafts).toHaveLength(0);
  });

  it('handlePaste takes image files from the clipboard and ignores text-only pastes', async () => {
    const { result } = renderHook(() => useComposerImages());
    const image = pngFile('pegada.png');
    const withImage = {
      clipboardData: {
        items: [
          { kind: 'string', type: 'text/plain', getAsFile: () => null },
          { kind: 'file', type: 'image/png', getAsFile: () => image },
        ],
      } as unknown as DataTransfer,
    };
    let took = false;
    act(() => {
      took = result.current.handlePaste(withImage);
    });
    expect(took).toBe(true);
    await waitFor(() => expect(result.current.drafts).toHaveLength(1));

    const textOnly = {
      clipboardData: {
        items: [{ kind: 'string', type: 'text/plain', getAsFile: () => null }],
      } as unknown as DataTransfer,
    };
    expect(result.current.handlePaste(textOnly)).toBe(false);
  });
});
