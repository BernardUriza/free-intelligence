'use client';

/**
 * The knowledge rail's data: what is in a project's corpus, and how full it is.
 *
 * ONE request for one panel (`GET /projects/{id}/documents` returns both halves),
 * because the meter is drawn directly above the grid and two requests would open
 * a window where the two disagree.
 *
 * `maxBytes`/`maxDocs` arrive as `null` when no quota is configured. That means
 * UNLIMITED and it stays `null` all the way to the meter — the component refuses
 * to draw a bar for it rather than inventing a denominator.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { authHeaders } from './og118Token';
import { proyectosActivos } from './og118Flags';

export interface Og118ProjectDocument {
  docId: string;
  chunks: number;
  status?: string;
}

export interface Og118ProjectCapacity {
  docs: number;
  chunks: number;
  bytes: number;
  maxDocs: number | null;
  maxBytes: number | null;
}

export interface UseOg118ProjectDocuments {
  documents: Og118ProjectDocument[];
  capacity: Og118ProjectCapacity | null;
  /** False until the first fetch settles — the rail shows a placeholder, not "0 docs". */
  ready: boolean;
  /** The fetch failed; the rail says so instead of rendering an empty corpus. */
  failed: boolean;
  /** Re-fetch (after an upload). */
  refresh: () => void;
}

const API = process.env.NEXT_PUBLIC_OG118_API ?? 'http://localhost:8118';

export function useOg118ProjectDocuments(
  projectId: string | null,
  tokenReady: boolean = true,
): UseOg118ProjectDocuments {
  const [documents, setDocuments] = useState<Og118ProjectDocument[]>([]);
  const [capacity, setCapacity] = useState<Og118ProjectCapacity | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [nonce, setNonce] = useState(0);
  // A stale response from the PREVIOUS project must never paint the current one:
  // switching projects fast otherwise shows someone else's document list for a
  // beat, which reads as data leaking between projects.
  const currentRef = useRef<string | null>(projectId);
  currentRef.current = projectId;

  useEffect(() => {
    if (!projectId || !tokenReady || !proyectosActivos()) {
      setDocuments([]);
      setCapacity(null);
      setReady(!projectId);
      setFailed(false);
      return;
    }
    let cancelled = false;
    setReady(false);
    setFailed(false);
    (async () => {
      try {
        const res = await fetch(
          `${API}/projects/${encodeURIComponent(projectId)}/documents`,
          { headers: { ...authHeaders() } },
        );
        if (cancelled || currentRef.current !== projectId) return;
        if (!res.ok) {
          setFailed(true);
          return;
        }
        const body = (await res.json()) as {
          documents?: Og118ProjectDocument[];
          capacity?: Og118ProjectCapacity;
        };
        if (cancelled || currentRef.current !== projectId) return;
        setDocuments(body.documents ?? []);
        setCapacity(body.capacity ?? null);
      } catch {
        if (!cancelled) setFailed(true);
      } finally {
        if (!cancelled && currentRef.current === projectId) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, tokenReady, nonce]);

  const refresh = useCallback(() => setNonce((n) => n + 1), []);

  return { documents, capacity, ready, failed, refresh };
}
