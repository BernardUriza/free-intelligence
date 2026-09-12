// @vitest-environment jsdom
/**
 * useOg118ConversationSync — el pull que trae los appends del worker al hilo
 * abierto. Pinea cuándo SÍ pide recarga (intervalo con la pestaña visible,
 * volver a la pestaña, foco) y cuándo no (oculta, streaming, modo local).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { cleanup, renderHook } from '@testing-library/react';
import { useOg118ConversationSync } from '../useOg118ConversationSync';

function setHidden(hidden: boolean) {
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden });
}

describe('useOg118ConversationSync', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setHidden(false);
  });
  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it('pide reloadActive en cada tick del intervalo con la pestaña visible', async () => {
    const reloadActive = vi.fn(async () => {});
    renderHook(() =>
      useOg118ConversationSync({ enabled: true, streaming: false, reloadActive, intervalMs: 1000 }),
    );
    expect(reloadActive).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1000);
    expect(reloadActive).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(2000);
    expect(reloadActive).toHaveBeenCalledTimes(3);
  });

  it('no pide nada con la pestaña oculta, y sí al volver a verse', async () => {
    const reloadActive = vi.fn(async () => {});
    setHidden(true);
    renderHook(() =>
      useOg118ConversationSync({ enabled: true, streaming: false, reloadActive, intervalMs: 1000 }),
    );
    await vi.advanceTimersByTimeAsync(3000);
    expect(reloadActive).not.toHaveBeenCalled();

    setHidden(false);
    document.dispatchEvent(new Event('visibilitychange'));
    expect(reloadActive).toHaveBeenCalledTimes(1);
  });

  it('el foco de la ventana dispara un pull', () => {
    const reloadActive = vi.fn(async () => {});
    renderHook(() =>
      useOg118ConversationSync({ enabled: true, streaming: false, reloadActive, intervalMs: 1000 }),
    );
    window.dispatchEvent(new Event('focus'));
    expect(reloadActive).toHaveBeenCalledTimes(1);
  });

  it('no pide nada mientras un turno está en streaming', async () => {
    const reloadActive = vi.fn(async () => {});
    const { rerender } = renderHook(
      ({ streaming }: { streaming: boolean }) =>
        useOg118ConversationSync({ enabled: true, streaming, reloadActive, intervalMs: 1000 }),
      { initialProps: { streaming: true } },
    );
    await vi.advanceTimersByTimeAsync(3000);
    window.dispatchEvent(new Event('focus'));
    expect(reloadActive).not.toHaveBeenCalled();

    rerender({ streaming: false });
    await vi.advanceTimersByTimeAsync(1000);
    expect(reloadActive).toHaveBeenCalledTimes(1);
  });

  it('en modo local (IndexedDB) no hay otro escritor: nunca pollea', async () => {
    const reloadActive = vi.fn(async () => {});
    renderHook(() =>
      useOg118ConversationSync({ enabled: false, streaming: false, reloadActive, intervalMs: 1000 }),
    );
    await vi.advanceTimersByTimeAsync(3000);
    window.dispatchEvent(new Event('focus'));
    expect(reloadActive).not.toHaveBeenCalled();
  });

  it('no encima un pull sobre otro en vuelo, y un fallo no rompe el siguiente tick', async () => {
    let release: () => void = () => {};
    const reloadActive = vi
      .fn()
      .mockImplementationOnce(() => new Promise<void>((r) => { release = r; }))
      .mockImplementationOnce(() => Promise.reject(new Error('500')))
      .mockImplementation(async () => {});
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    renderHook(() =>
      useOg118ConversationSync({ enabled: true, streaming: false, reloadActive, intervalMs: 1000 }),
    );
    await vi.advanceTimersByTimeAsync(2000);
    expect(reloadActive).toHaveBeenCalledTimes(1);
    release();
    await vi.advanceTimersByTimeAsync(1000);
    expect(reloadActive).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(1000);
    expect(reloadActive).toHaveBeenCalledTimes(3);
    expect(errorSpy).toHaveBeenCalled();
    errorSpy.mockRestore();
  });
});
