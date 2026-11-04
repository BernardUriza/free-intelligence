'use client';

import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { Sparkles, X } from 'lucide-react';
import { AdminAlert, AdminButton } from '../admin-kit';
import { mapFormToCreateRequest } from './mappers';
import { PersonaForm } from './PersonaForm';
import { PersonaSheet } from './PersonaSheet';
import {
  DEFAULT_PERSONA_VALUES,
  validatePersonaCreate,
  type PersonaCreateFormValues,
  type PersonaFormValues,
} from './schema';
import { errorMessage, type Persona, type PersonaHideableField, type PersonaOption, type PersonaStore } from './types';

export interface PersonaCreateModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  store: Pick<PersonaStore, 'create'>;
  onCreated: (persona: Persona) => void;
  modelOptions: readonly PersonaOption[];
  voiceOptions?: readonly PersonaOption[];
  hiddenFields?: readonly PersonaHideableField[];
  initialValues?: Partial<PersonaCreateFormValues>;
  /** Consumer-specific fields rendered above the form (e.g. a slot picker). */
  renderExtraFields?: () => ReactNode;
  /** Runs after the form validates and before `store.create`; a string blocks submit and is shown as the error. */
  validateExtra?: () => string | null;
  title?: string;
  subtitle?: string;
  submitLabel?: string;
}

function startingValues(
  initialValues: Partial<PersonaCreateFormValues> | undefined,
  modelOptions: readonly PersonaOption[],
  voiceOptions: readonly PersonaOption[],
): PersonaCreateFormValues {
  const values = { ...DEFAULT_PERSONA_VALUES, ...initialValues };
  if (!initialValues?.model && modelOptions.length && !modelOptions.some((o) => o.value === values.model)) {
    values.model = modelOptions[0].value;
  }
  if (initialValues?.voice === undefined && !voiceOptions.some((o) => o.value === values.voice)) {
    values.voice = null;
  }
  return values;
}

export function PersonaCreateModal({
  open,
  onOpenChange,
  store,
  onCreated,
  modelOptions,
  voiceOptions = [],
  hiddenFields = [],
  initialValues,
  renderExtraFields,
  validateExtra,
  title = 'Crear nueva persona',
  subtitle = 'Define una nueva personalidad de IA',
  submitLabel = 'Crear persona',
}: PersonaCreateModalProps) {
  const titleId = useId();
  const startRef = useRef(() => startingValues(initialValues, modelOptions, voiceOptions));
  startRef.current = () => startingValues(initialValues, modelOptions, voiceOptions);
  const [values, setValues] = useState<PersonaCreateFormValues>(() => startRef.current());
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [creating, setCreating] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setValues(startRef.current());
      setErrors({});
      setApiError(null);
    }
  }, [open]);

  const close = useCallback(() => {
    if (!creating) onOpenChange(false);
  }, [creating, onOpenChange]);

  const submit = useCallback(async () => {
    const validation = validatePersonaCreate(values);
    if (!validation.success || !validation.data) {
      setErrors(validation.errors ?? {});
      return;
    }
    const extraError = validateExtra?.() ?? null;
    if (extraError) {
      setApiError(extraError);
      return;
    }
    setErrors({});
    setApiError(null);
    setCreating(true);
    try {
      const persona = await store.create(mapFormToCreateRequest(validation.data, hiddenFields));
      onCreated(persona);
      onOpenChange(false);
    } catch (err) {
      setApiError(errorMessage(err, 'Error inesperado al crear la persona'));
    } finally {
      setCreating(false);
    }
  }, [values, validateExtra, store, hiddenFields, onCreated, onOpenChange]);

  const change = useCallback((next: PersonaFormValues) => {
    setValues(next as PersonaCreateFormValues);
    setErrors((prev) => (Object.keys(prev).length ? {} : prev));
  }, []);

  if (!open) return null;

  return (
    <PersonaSheet
      onDismiss={close}
      labelledBy={titleId}
      header={
        <>
          <div>
            <h2 id={titleId} className="fi-persona-title">
              <Sparkles size={20} aria-hidden="true" />
              {title}
            </h2>
            <p className="fi-persona-subtitle">{subtitle}</p>
          </div>
          <AdminButton variant="ghost" iconOnly icon={X} onClick={close} disabled={creating} aria-label="Cerrar" />
        </>
      }
      footer={
        <>
          <p className="fi-persona-subtitle">
            <span className="fi-persona-required">*</span> Campos requeridos
          </p>
          <div className="fi-persona-actions">
            <AdminButton onClick={close} disabled={creating}>
              Cancelar
            </AdminButton>
            <AdminButton
              variant="primary"
              icon={Sparkles}
              loading={creating}
              disabled={creating}
              onClick={() => void submit()}
            >
              {creating ? 'Creando...' : submitLabel}
            </AdminButton>
          </div>
        </>
      }
    >
      <form
        className="fi-persona-stack"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        {renderExtraFields?.()}
        <PersonaForm
          value={values}
          onChange={change}
          mode="create"
          modelOptions={modelOptions}
          voiceOptions={voiceOptions}
          hiddenFields={hiddenFields}
          disabled={creating}
          errors={errors}
          showExamplesSummary
        />
        {apiError ? <AdminAlert>{apiError}</AdminAlert> : null}
      </form>
    </PersonaSheet>
  );
}
