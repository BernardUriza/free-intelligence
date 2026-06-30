'use client';

/**
 * useOg118Elements — loads the active "elementos" catalog (GET /elements) and owns
 * the user's active selection (persisted per identity via og118Element). The
 * selected slug flows into useOg118Agent, which sends it as the chat's `element`.
 *
 * The list always leads with the BASE companion (empty slug) so the user can
 * switch back to plain og118 — selecting it sends no element. Catalog fetch is
 * active-only (the backend filters); a fetch failure degrades to base-only, never
 * throws into the render.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  BASE_ELEMENT_SLUG,
  getSelectedElement,
  setSelectedElement,
  type Og118Element,
} from './og118Element';
import { authHeaders } from './og118Token';

const API = process.env.NEXT_PUBLIC_OG118_API ?? 'http://localhost:8118';

export interface Og118ElementsHook {
  /** BASE companion first, then each active element. */
  elements: Og118Element[];
  /** The selected slug ('' = base companion). */
  selected: string;
  /** Select an element by slug and persist it. */
  select: (slug: string) => void;
  loading: boolean;
}

const BASE_OPTION: Og118Element = {
  id: 'element-base',
  atomicNumber: 0,
  symbol: 'og',
  slug: BASE_ELEMENT_SLUG,
  displayName: 'og118 (base)',
  displayLabel: 'og118 (base)',
  status: 'active',
  aliases: [],
};

export function useOg118Elements(userId: string | null): Og118ElementsHook {
  const [active, setActive] = useState<Og118Element[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string>(BASE_ELEMENT_SLUG);

  // Hydrate the persisted selection once the identity is known (it can change
  // when a different account signs in on the same browser).
  useEffect(() => {
    setSelected(getSelectedElement(userId));
  }, [userId]);

  useEffect(() => {
    let alive = true;
    fetch(`${API}/elements`, { headers: { ...authHeaders() } })
      .then((r) => (r.ok ? r.json() : { elements: [] }))
      .then((data: { elements?: Og118Element[] }) => {
        if (alive) setActive(data.elements ?? []);
      })
      .catch(() => {
        if (alive) setActive([]);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const select = useCallback(
    (slug: string) => {
      setSelected(slug);
      setSelectedElement(userId, slug);
    },
    [userId],
  );

  return { elements: [BASE_OPTION, ...active], selected, select, loading };
}
