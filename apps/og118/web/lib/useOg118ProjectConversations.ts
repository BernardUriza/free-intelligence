'use client';

/**
 * The "Recents" list of a project detail: the account's conversations filtered
 * to one project, server-side.
 *
 * Filtered by the SERVER (`GET /conversations?projectId=`) and not here, because
 * doing it in the browser means downloading every transcript summary in the
 * account to show the handful that belong to the project on screen.
 */

import { useEffect, useRef, useState } from 'react';
import { authHeaders } from './og118Token';

export interface Og118ProjectConversation {
  id: string;
  title: string;
  updatedAt: string;
}

const API = process.env.NEXT_PUBLIC_OG118_API ?? 'http://localhost:8118';

export function useOg118ProjectConversations(
  projectId: string | null,
  tokenReady: boolean = true,
): { conversations: Og118ProjectConversation[]; ready: boolean } {
  const [conversations, setConversations] = useState<Og118ProjectConversation[]>([]);
  const [ready, setReady] = useState(false);
  const currentRef = useRef<string | null>(projectId);
  currentRef.current = projectId;

  useEffect(() => {
    if (!projectId || !tokenReady) {
      setConversations([]);
      setReady(!projectId);
      return;
    }
    let cancelled = false;
    setReady(false);
    (async () => {
      try {
        const res = await fetch(
          `${API}/conversations?projectId=${encodeURIComponent(projectId)}`,
          { headers: { ...authHeaders() } },
        );
        if (cancelled || currentRef.current !== projectId || !res.ok) return;
        const body = (await res.json()) as {
          conversations?: { id: string; title?: string; updatedAt?: string }[];
        };
        if (cancelled || currentRef.current !== projectId) return;
        setConversations(
          (body.conversations ?? []).map((c) => ({
            id: c.id,
            title: c.title || 'Sin título',
            updatedAt: c.updatedAt ?? '',
          })),
        );
      } catch {
        /* offline — an empty Recents is the honest render, and `ready` still flips */
      } finally {
        if (!cancelled && currentRef.current === projectId) setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [projectId, tokenReady]);

  return { conversations, ready };
}
