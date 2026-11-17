'use client';

/**
 * The account's stored files (`GET /files`): what a chat saved through its
 * `save_file` tool, plus the quota. Downloads go through `fetch` because the
 * route wants the bearer, which a plain link cannot carry.
 */

import { useCallback, useEffect, useState } from 'react';
import { authHeaders } from './og118Token';

export interface Og118File {
  id: string;
  name: string;
  contentType: string;
  size: number;
  createdAt: string;
  conversationId?: string;
}

export interface UseOg118Files {
  files: Og118File[];
  usedBytes: number;
  quotaBytes: number;
  ready: boolean;
  failed: boolean;
  refresh: () => void;
  download: (file: Og118File) => Promise<boolean>;
  remove: (file: Og118File) => Promise<boolean>;
}

const API = process.env.NEXT_PUBLIC_OG118_API ?? 'http://localhost:8118';

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB'];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value >= 10 ? Math.round(value) : value.toFixed(1)} ${units[unit]}`;
}

export function useOg118Files(enabled: boolean): UseOg118Files {
  const [files, setFiles] = useState<Og118File[]>([]);
  const [usedBytes, setUsedBytes] = useState(0);
  const [quotaBytes, setQuotaBytes] = useState(0);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    setFailed(false);
    (async () => {
      try {
        const res = await fetch(`${API}/files`, { headers: { ...authHeaders() } });
        if (cancelled) return;
        if (!res.ok) {
          setFailed(true);
          return;
        }
        const body = (await res.json()) as {
          files?: Og118File[];
          usedBytes?: number;
          quotaBytes?: number;
        };
        if (cancelled) return;
        setFiles(body.files ?? []);
        setUsedBytes(body.usedBytes ?? 0);
        setQuotaBytes(body.quotaBytes ?? 0);
      } catch {
        if (!cancelled) setFailed(true);
      } finally {
        if (!cancelled) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [enabled, nonce]);

  const refresh = useCallback(() => setNonce((n) => n + 1), []);

  const download = useCallback(async (file: Og118File) => {
    try {
      const res = await fetch(`${API}/files/${file.id}`, { headers: { ...authHeaders() } });
      if (!res.ok) return false;
      const url = URL.createObjectURL(await res.blob());
      const link = document.createElement('a');
      link.href = url;
      link.download = file.name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
      return true;
    } catch {
      return false;
    }
  }, []);

  const remove = useCallback(
    async (file: Og118File) => {
      try {
        const res = await fetch(`${API}/files/${file.id}`, {
          method: 'DELETE',
          headers: { ...authHeaders() },
        });
        if (!res.ok) return false;
        refresh();
        return true;
      } catch {
        return false;
      }
    },
    [refresh],
  );

  return { files, usedBytes, quotaBytes, ready, failed, refresh, download, remove };
}
