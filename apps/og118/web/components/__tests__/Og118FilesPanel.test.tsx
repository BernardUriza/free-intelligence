import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { Og118FilesPanel } from '../Og118FilesPanel';
import { formatBytes } from '../../lib/useOg118Files';

const LISTING = {
  files: [
    {
      id: 'a'.repeat(32),
      name: 'datos.h5',
      contentType: 'application/x-hdf5',
      size: 200000,
      createdAt: '2026-11-17T18:00:00Z',
      conversationId: 'conv-1',
    },
  ],
  usedBytes: 200000,
  quotaBytes: 1073741824,
};

function stubFetch() {
  const calls: { url: string; method: string }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      calls.push({ url, method: init?.method ?? 'GET' });
      return new Response(JSON.stringify(init?.method === 'DELETE' ? { deleted: 'x' } : LISTING), { status: 200 });
    }),
  );
  return calls;
}

afterEach(() => vi.unstubAllGlobals());

describe('Og118FilesPanel', () => {
  it('stays out of the sidebar until the account is usable, and asks nothing', () => {
    const calls = stubFetch();
    render(<Og118FilesPanel enabled={false} />);
    expect(screen.queryByRole('button', { name: /Archivos/ })).toBeNull();
    expect(calls).toEqual([]);
  });

  it('lists what the chats saved, with the chat each file came from', async () => {
    const calls = stubFetch();
    render(<Og118FilesPanel enabled conversationTitle={(id) => (id === 'conv-1' ? 'Mi análisis' : undefined)} />);
    expect(calls).toEqual([]);

    fireEvent.click(screen.getByRole('button', { name: /Archivos/ }));

    expect(await screen.findByText('datos.h5')).toBeTruthy();
    expect(screen.getByText(/195 KB · .* · Mi análisis/)).toBeTruthy();
    expect(screen.getByText('195 KB de 1.0 GB usados')).toBeTruthy();
    expect(calls[0].url.endsWith('/files')).toBe(true);
  });

  it('deletes only after the confirm, then reloads the list', async () => {
    const calls = stubFetch();
    const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true);
    render(<Og118FilesPanel enabled />);
    fireEvent.click(screen.getByRole('button', { name: /Archivos/ }));
    const borrar = await screen.findByRole('button', { name: 'Borrar datos.h5' });

    fireEvent.click(borrar);
    expect(calls.filter((c) => c.method === 'DELETE')).toEqual([]);

    fireEvent.click(borrar);
    await waitFor(() => expect(calls.filter((c) => c.method === 'DELETE')).toHaveLength(1));
    expect(calls.find((c) => c.method === 'DELETE')?.url.endsWith(`/files/${'a'.repeat(32)}`)).toBe(true);
    confirm.mockRestore();
  });
});

describe('formatBytes', () => {
  it('reads like a file manager', () => {
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(32 * 1024 * 1024)).toBe('32 MB');
  });
});
