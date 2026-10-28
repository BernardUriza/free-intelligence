'use client';

import { useCallback, useId, useState, type FormEvent } from 'react';
import { X } from 'lucide-react';
import { AdminAlert, AdminButton } from '../admin-kit';
import { ModelSheet } from './ModelSheet';
import { COST_TIER_INFO, PROVIDER_INFO } from './format';
import { errorMessage, type CostTier, type LLMModel, type LLMModelCreate, type LLMProvider, type ModelCatalogStore } from './types';

export interface LLMModelFormSheetProps {
  /** Present = edit that model; absent = create a new one. */
  model?: LLMModel;
  store: Pick<ModelCatalogStore, 'createModel' | 'updateModel'>;
  onClose: () => void;
  onSaved: (model: LLMModel) => void;
}

function initialValues(model?: LLMModel): LLMModelCreate {
  return {
    id: model?.id ?? '',
    label: model?.label ?? '',
    provider: model?.provider ?? 'openai',
    cost_tier: model?.cost_tier ?? 'medium',
    max_tokens: model?.max_tokens ?? 4096,
    context_window: model?.context_window ?? 128000,
    is_active: model?.is_active ?? true,
    description: model?.description ?? '',
  };
}

export function sanitizeModelId(value: string): string {
  return value.toLowerCase().replace(/\s/g, '-');
}

export function LLMModelFormSheet({ model, store, onClose, onSaved }: LLMModelFormSheetProps) {
  const isCreate = !model;
  const titleId = useId();
  const fieldId = useId();
  const [values, setValues] = useState<LLMModelCreate>(() => initialValues(model));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = useCallback(<K extends keyof LLMModelCreate>(key: K, value: LLMModelCreate[K]) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (isCreate && !values.id.trim()) return setError('El ID del modelo es requerido');
    if (!values.label.trim()) return setError('El label es requerido');
    setSaving(true);
    setError(null);
    try {
      const { id: _id, ...update } = values;
      const saved = model ? await store.updateModel(model.id, update) : await store.createModel(values);
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(errorMessage(err, 'Error al guardar'));
    } finally {
      setSaving(false);
    }
  };

  const f = (name: string) => `${fieldId}-${name}`;
  return (
    <ModelSheet
      onDismiss={onClose}
      labelledBy={titleId}
      header={
        <div className="fi-admin-head-row">
          <h2 id={titleId} className="fi-mc-title">
            {isCreate ? 'Nuevo modelo LLM' : 'Editar modelo'}
          </h2>
          <AdminButton variant="ghost" iconOnly icon={X} aria-label="Cerrar" onClick={onClose} />
        </div>
      }
    >
      <form className="fi-mc-stack" onSubmit={submit} noValidate>
        {isCreate ? (
          <div className="fi-mc-field">
            <label className="fi-mc-label" htmlFor={f('id')}>
              ID del modelo *
            </label>
            <input
              id={f('id')}
              className="fi-mc-input fi-mc-mono"
              value={values.id}
              placeholder="gpt-4o-mini"
              onChange={(e) => set('id', sanitizeModelId(e.target.value))}
            />
            <p className="fi-mc-hint">Identificador único (sin espacios, minúsculas)</p>
          </div>
        ) : null}
        <div className="fi-mc-field">
          <label className="fi-mc-label" htmlFor={f('label')}>
            Label (nombre visible) *
          </label>
          <input
            id={f('label')}
            className="fi-mc-input"
            value={values.label}
            placeholder="GPT-4o Mini (Balance, $$)"
            onChange={(e) => set('label', e.target.value)}
          />
        </div>
        <div className="fi-mc-grid2">
          <div className="fi-mc-field">
            <label className="fi-mc-label" htmlFor={f('provider')}>
              Proveedor
            </label>
            <select
              id={f('provider')}
              className="fi-mc-input"
              value={values.provider}
              onChange={(e) => set('provider', e.target.value as LLMProvider)}
            >
              {(Object.keys(PROVIDER_INFO) as LLMProvider[]).map((key) => (
                <option key={key} value={key}>
                  {PROVIDER_INFO[key].label}
                </option>
              ))}
            </select>
          </div>
          <div className="fi-mc-field">
            <label className="fi-mc-label" htmlFor={f('cost')}>
              Nivel de costo
            </label>
            <select
              id={f('cost')}
              className="fi-mc-input"
              value={values.cost_tier}
              onChange={(e) => set('cost_tier', e.target.value as CostTier)}
            >
              {(Object.keys(COST_TIER_INFO) as CostTier[]).map((key) => (
                <option key={key} value={key}>
                  {COST_TIER_INFO[key].symbol} {COST_TIER_INFO[key].label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="fi-mc-grid2">
          <div className="fi-mc-field">
            <label className="fi-mc-label" htmlFor={f('max')}>
              Max tokens (output)
            </label>
            <input
              id={f('max')}
              type="number"
              inputMode="numeric"
              className="fi-mc-input"
              min={1}
              max={1000000}
              value={values.max_tokens}
              onChange={(e) => set('max_tokens', parseInt(e.target.value, 10) || 0)}
            />
          </div>
          <div className="fi-mc-field">
            <label className="fi-mc-label" htmlFor={f('ctx')}>
              Ventana de contexto
            </label>
            <input
              id={f('ctx')}
              type="number"
              inputMode="numeric"
              className="fi-mc-input"
              min={1024}
              max={2000000}
              value={values.context_window}
              onChange={(e) => set('context_window', parseInt(e.target.value, 10) || 0)}
            />
          </div>
        </div>
        <div className="fi-mc-field">
          <label className="fi-mc-label" htmlFor={f('desc')}>
            Descripción
          </label>
          <textarea
            id={f('desc')}
            className="fi-mc-input"
            rows={2}
            placeholder="Descripción del modelo y casos de uso..."
            value={values.description ?? ''}
            onChange={(e) => set('description', e.target.value)}
          />
        </div>
        <label className="fi-mc-check">
          <input type="checkbox" checked={values.is_active} onChange={(e) => set('is_active', e.target.checked)} />
          Modelo activo (disponible para selección)
        </label>
        {error ? <AdminAlert>{error}</AdminAlert> : null}
        <div className="fi-mc-grid2">
          <AdminButton onClick={onClose}>Cancelar</AdminButton>
          <AdminButton type="submit" variant="primary" loading={saving} disabled={saving}>
            {isCreate ? 'Crear modelo' : 'Guardar cambios'}
          </AdminButton>
        </div>
      </form>
    </ModelSheet>
  );
}
