'use client';

import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { Brain, FileText, List, Loader2, Save, Settings, Trash2, X, Zap, type LucideIcon } from 'lucide-react';
import { AdminAlert, AdminButton } from '../admin-kit';
import { mapFormToUpdateRequest, mapPersonaToFormValues } from './mappers';
import { PersonaExamplesTab, PersonaPromptTab, PersonaTestTab } from './PersonaEditorTabs';
import { PersonaForm } from './PersonaForm';
import { PersonaSheet } from './PersonaSheet';
import { validatePersonaUpdate, type PersonaFormValues } from './schema';
import {
  defaultPersonaConfirm,
  errorMessage,
  type Persona,
  type PersonaConfirm,
  type PersonaHideableField,
  type PersonaOption,
  type PersonaStore,
} from './types';

export type PersonaEditorTab = 'config' | 'prompt' | 'examples' | 'test';

export interface PersonaEditorProps {
  personaId: string;
  open: boolean;
  onClose: () => void;
  onSaved: (persona: Persona) => void;
  store: Pick<PersonaStore, 'get' | 'update' | 'test'> & Partial<Pick<PersonaStore, 'remove'>>;
  modelOptions: readonly PersonaOption[];
  voiceOptions?: readonly PersonaOption[];
  hiddenFields?: readonly PersonaHideableField[];
  /** Shows the delete action when given together with `store.remove`. */
  onDeleted?: (personaId: string) => void;
  confirm?: PersonaConfirm;
  deleteConfirmMessage?: (persona: Persona) => string;
  locale?: string;
}

const TABS: { value: PersonaEditorTab; label: string; icon: LucideIcon }[] = [
  { value: 'config', label: 'Configuración', icon: Settings },
  { value: 'prompt', label: 'System Prompt', icon: FileText },
  { value: 'examples', label: 'Examples', icon: List },
  { value: 'test', label: 'Probar', icon: Zap },
];

export const defaultDeleteConfirmMessage = (persona: Persona) =>
  `¿Eliminar la persona "${persona.name}"? Esta acción no se puede deshacer.`;

export function PersonaEditor({
  personaId,
  open,
  onClose,
  onSaved,
  store,
  modelOptions,
  voiceOptions,
  hiddenFields = [],
  onDeleted,
  confirm = defaultPersonaConfirm,
  deleteConfirmMessage = defaultDeleteConfirmMessage,
  locale = 'es-MX',
}: PersonaEditorProps) {
  const titleId = useId();
  const [persona, setPersona] = useState<Persona | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<'save' | 'delete' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [tab, setTab] = useState<PersonaEditorTab>('config');
  const storeRef = useRef(store);
  storeRef.current = store;

  useEffect(() => {
    if (!open || !personaId) return;
    let alive = true;
    setLoading(true);
    setError(null);
    setTab('config');
    storeRef.current
      .get(personaId)
      .then((data) => alive && setPersona(data))
      .catch((err) => alive && setError(errorMessage(err, 'Error al cargar la persona')))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [open, personaId]);

  const patch = useCallback((updates: Partial<Persona>) => {
    setPersona((prev) => (prev ? { ...prev, ...updates } : prev));
    setFieldErrors((prev) => (Object.keys(prev).length ? {} : prev));
  }, []);

  const save = async () => {
    if (!persona) return;
    const validation = validatePersonaUpdate(mapPersonaToFormValues(persona));
    if (!validation.success || !validation.data) {
      const errors = validation.errors ?? {};
      setFieldErrors(errors);
      setError(Object.values(errors)[0] ?? 'Revisa los campos');
      return;
    }
    setBusy('save');
    setError(null);
    try {
      const updated = await store.update(personaId, mapFormToUpdateRequest(validation.data, hiddenFields));
      onSaved(updated);
      onClose();
    } catch (err) {
      setError(errorMessage(err, 'Error al guardar la persona'));
    } finally {
      setBusy(null);
    }
  };

  const remove = async () => {
    if (!persona || !store.remove || !onDeleted) return;
    if (!(await confirm(deleteConfirmMessage(persona)))) return;
    setBusy('delete');
    setError(null);
    try {
      await store.remove(personaId);
      onDeleted(personaId);
      onClose();
    } catch (err) {
      setError(errorMessage(err, 'Error al eliminar la persona'));
    } finally {
      setBusy(null);
    }
  };

  if (!open) return null;

  const tabs = TABS.filter((t) => !(t.value === 'examples' && hiddenFields.includes('examples')));
  const canDelete = Boolean(store.remove && onDeleted);

  return (
    <PersonaSheet
      placement="side"
      onDismiss={onClose}
      labelledBy={titleId}
      header={
        <>
          <div style={{ minWidth: 0 }}>
            <h2 id={titleId} className="fi-persona-title">
              <Brain size={22} aria-hidden="true" />
              {persona ? `Editar persona: ${persona.name}` : 'Editar persona'}
            </h2>
            {persona?.version !== undefined || persona?.last_updated ? (
              <p className="fi-persona-subtitle">
                {persona?.version !== undefined ? `Versión ${persona.version}` : null}
                {persona?.last_updated
                  ? ` · Última actualización: ${new Date(persona.last_updated).toLocaleDateString(locale)}`
                  : null}
              </p>
            ) : null}
          </div>
          <AdminButton variant="ghost" iconOnly icon={X} onClick={onClose} aria-label="Cerrar" />
          {persona ? (
            <div className="fi-persona-tabs" role="tablist">
              {tabs.map((t) => (
                <AdminButton
                  key={t.value}
                  role="tab"
                  className="fi-persona-tab"
                  variant="ghost"
                  icon={t.icon}
                  aria-selected={tab === t.value}
                  onClick={() => setTab(t.value)}
                >
                  {t.label}
                </AdminButton>
              ))}
            </div>
          ) : null}
        </>
      }
      footer={
        persona ? (
          <>
            <div className="fi-persona-actions">
              {canDelete ? (
                <AdminButton
                  variant="danger"
                  icon={Trash2}
                  loading={busy === 'delete'}
                  disabled={busy !== null}
                  onClick={() => void remove()}
                >
                  Eliminar
                </AdminButton>
              ) : null}
            </div>
            <div className="fi-persona-actions">
              <AdminButton onClick={onClose} disabled={busy !== null}>
                Cancelar
              </AdminButton>
              <AdminButton
                variant="primary"
                icon={Save}
                loading={busy === 'save'}
                disabled={busy !== null}
                onClick={() => void save()}
              >
                Guardar cambios
              </AdminButton>
            </div>
          </>
        ) : undefined
      }
    >
      {loading ? (
        <div className="fi-persona-empty" aria-busy="true">
          <Loader2 size={32} className="fi-admin-spin" aria-label="Cargando" />
        </div>
      ) : (
        <div className="fi-persona-stack">
          {error ? <AdminAlert>{error}</AdminAlert> : null}
          {persona && tab === 'config' ? (
            <PersonaForm
              mode="edit"
              personaId={persona.id}
              value={mapPersonaToFormValues(persona)}
              onChange={(v: PersonaFormValues) => patch(v as Partial<Persona>)}
              modelOptions={modelOptions}
              voiceOptions={voiceOptions}
              hiddenFields={hiddenFields}
              errors={fieldErrors}
              showSystemPrompt={false}
            />
          ) : null}
          {persona && tab === 'prompt' ? <PersonaPromptTab persona={persona} onChange={patch} /> : null}
          {persona && tab === 'examples' ? <PersonaExamplesTab persona={persona} onChange={patch} /> : null}
          {persona && tab === 'test' ? <PersonaTestTab personaId={persona.id} store={store} /> : null}
        </div>
      )}
    </PersonaSheet>
  );
}
