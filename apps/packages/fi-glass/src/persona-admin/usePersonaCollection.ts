'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { defaultDeleteConfirmMessage } from './PersonaEditor';
import { defaultPersonaConfirm, errorMessage, type Persona, type PersonaConfirm, type PersonaStore } from './types';

export interface UsePersonaCollectionOptions {
  confirm?: PersonaConfirm;
  deleteConfirmMessage?: (persona: Persona) => string;
}

export interface PersonaCollection {
  personas: Persona[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  /** Insert or replace by id (after a create or a save). */
  upsert: (persona: Persona) => void;
  /** Drop by id without calling the store (after the editor already deleted it). */
  forget: (personaId: string) => void;
  /** Confirms, then calls `store.remove`. Resolves true only if the persona was deleted. */
  remove: (persona: Persona) => Promise<boolean>;
  removeError: string | null;
  clearRemoveError: () => void;
}

export function usePersonaCollection(
  store: Pick<PersonaStore, 'list' | 'remove'>,
  { confirm = defaultPersonaConfirm, deleteConfirmMessage = defaultDeleteConfirmMessage }: UsePersonaCollectionOptions = {},
): PersonaCollection {
  const storeRef = useRef(store);
  storeRef.current = store;
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [removeError, setRemoveError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPersonas(await storeRef.current.list());
    } catch (err) {
      setError(errorMessage(err, 'Error al cargar las personas'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const upsert = useCallback((persona: Persona) => {
    setPersonas((prev) =>
      prev.some((p) => p.id === persona.id) ? prev.map((p) => (p.id === persona.id ? persona : p)) : [...prev, persona],
    );
  }, []);

  const forget = useCallback((personaId: string) => {
    setPersonas((prev) => prev.filter((p) => p.id !== personaId));
  }, []);

  const remove = useCallback(
    async (persona: Persona) => {
      if (!(await confirm(deleteConfirmMessage(persona)))) return false;
      setRemoveError(null);
      try {
        await storeRef.current.remove(persona.id);
        forget(persona.id);
        return true;
      } catch (err) {
        setRemoveError(errorMessage(err, 'Error al eliminar la persona'));
        return false;
      }
    },
    [confirm, deleteConfirmMessage, forget],
  );

  return {
    personas,
    loading,
    error,
    reload,
    upsert,
    forget,
    remove,
    removeError,
    clearRemoveError: useCallback(() => setRemoveError(null), []),
  };
}
