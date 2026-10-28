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
  ELEMENT_ENGINES,
  getSelectedElement,
  setSelectedElement,
  type Og118Element,
  type Og118ElementDraft,
  type Og118EmptySlot,
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
  /** Whether this account may claim a slot (the server's allowlist decides). */
  canCreate: boolean;
  /** Empty slots a new element can take. */
  slots: Og118EmptySlot[];
  /** Claim a slot with a persona; resolves to the new slug or throws the server's reason. */
  create: (draft: Og118ElementDraft) => Promise<string>;
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
  description: 'Compañero base de og118 — sin persona de elemento, respuesta directa.',
  engine: null,
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

  const [canCreate, setCanCreate] = useState(false);
  const [slots, setSlots] = useState<Og118EmptySlot[]>([]);
  const [revision, setRevision] = useState(0);

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
  }, [revision]);

  useEffect(() => {
    if (!userId) return;
    let alive = true;
    fetch(`${API}/elements/slots`, { headers: { ...authHeaders() } })
      .then((r) => (r.ok ? r.json() : { canCreate: false, slots: [] }))
      .then((data: { canCreate?: boolean; slots?: Og118EmptySlot[] }) => {
        if (!alive) return;
        setCanCreate(Boolean(data.canCreate));
        setSlots(data.slots ?? []);
      })
      .catch(() => {
        if (alive) setCanCreate(false);
      });
    return () => {
      alive = false;
    };
  }, [userId, revision]);

  const select = useCallback(
    (slug: string) => {
      setSelected(slug);
      setSelectedElement(userId, slug);
    },
    [userId],
  );

  const create = useCallback(
    async (draft: Og118ElementDraft): Promise<string> => {
      const engine = ELEMENT_ENGINES.find((e) => e.id === draft.engine) ?? ELEMENT_ENGINES[0];
      const res = await fetch(`${API}/elements`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          atomicNumber: draft.atomicNumber,
          displayName: draft.displayName,
          personaId: draft.personaId,
          description: draft.description || null,
          aliases: draft.aliases,
          provider: engine.provider,
          model: engine.model,
          dna: draft.dna,
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = typeof body?.detail === 'string' ? body.detail : `HTTP ${res.status}`;
        throw new Error(detail);
      }
      const slug = slots.find((s) => s.atomicNumber === draft.atomicNumber)?.slug ?? '';
      setRevision((r) => r + 1);
      if (slug) select(slug);
      return slug;
    },
    [slots, select],
  );

  return { elements: [BASE_OPTION, ...active], selected, select, loading, canCreate, slots, create };
}
