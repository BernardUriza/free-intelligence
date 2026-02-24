/**
 * LLMModelModal
 *
 * Single Responsibility: Create/Edit form modal for LLM model configuration.
 * Handles form state, validation, and submission.
 *
 * Route: /admin/models
 */

'use client';

import { useState, useCallback } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import type { LLMModel, LLMModelCreate, LLMModelUpdate, LLMProvider, CostTier } from '@aurity-standalone/types/llm';
import { PROVIDER_INFO, COST_TIER_INFO } from '@aurity-standalone/types/llm';

// ── Types ───────────────────────────────────────────────────────────

interface LLMModelModalProps {
  mode: 'create' | 'edit';
  model?: LLMModel;
  onClose: () => void;
  onCreate?: (data: LLMModelCreate) => Promise<void>;
  onUpdate?: (data: LLMModelUpdate) => Promise<void>;
}

// ── Helpers ─────────────────────────────────────────────────────────

function buildInitialFormData(model?: LLMModel): LLMModelCreate {
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

function sanitizeModelId(value: string): string {
  return value.toLowerCase().replace(/\s/g, '-');
}

// ── Component ───────────────────────────────────────────────────────

export function LLMModelModal({ mode, model, onClose, onCreate, onUpdate }: LLMModelModalProps) {
  const [formData, setFormData] = useState<LLMModelCreate>(() => buildInitialFormData(model));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateField = useCallback(<K extends keyof LLMModelCreate>(
    key: K,
    value: LLMModelCreate[K],
  ) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    if (mode === 'create' && !formData.id.trim()) {
      setError('El ID del modelo es requerido');
      return;
    }
    if (!formData.label.trim()) {
      setError('El label es requerido');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      if (mode === 'create' && onCreate) {
        await onCreate(formData);
      } else if (mode === 'edit' && onUpdate) {
        const { id: _id, ...updateData } = formData;
        await onUpdate(updateData);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al guardar');
    } finally {
      setSaving(false);
    }
  }, [mode, formData, onCreate, onUpdate]);

  return (
    <div className="mdl-modal-overlay">
      <div className="mdl-modal-panel">
        <div className="mdl-modal-title-row">
          <h2 className="fi-title-xl">
            {mode === 'create' ? 'Nuevo Modelo LLM' : 'Editar Modelo'}
          </h2>
          <button onClick={onClose} className="fi-btn-close">
            <X className="mdl-close-icon" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mdl-form">
          {/* ID (only for create) */}
          {mode === 'create' && (
            <div>
              <label className="mdl-label">ID del Modelo *</label>
              <Input
                value={formData.id}
                onChange={(e) => updateField('id', sanitizeModelId(e.target.value))}
                placeholder="gpt-4o-mini"
                className="mdl-input-mono"
              />
              <p className="mdl-form-hint">
                Identificador único (sin espacios, minúsculas)
              </p>
            </div>
          )}

          {/* Label */}
          <div>
            <label className="mdl-label">Label (Nombre visible) *</label>
            <Input
              value={formData.label}
              onChange={(e) => updateField('label', e.target.value)}
              placeholder="GPT-4o Mini (Balance, $$)"
            />
          </div>

          {/* Provider & Cost Tier */}
          <div className="mdl-form-grid">
            <div>
              <label className="mdl-label">Proveedor</label>
              <Select
                value={formData.provider}
                onValueChange={(val) => updateField('provider', val as LLMProvider)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Seleccionar proveedor" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(PROVIDER_INFO).map(([key, info]) => (
                    <SelectItem key={key} value={key}>
                      {info.icon} {info.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="mdl-label">Nivel de Costo</label>
              <Select
                value={formData.cost_tier}
                onValueChange={(val) => updateField('cost_tier', val as CostTier)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Seleccionar nivel" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(COST_TIER_INFO).map(([key, info]) => (
                    <SelectItem key={key} value={key}>
                      {info.icon} {info.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Max Tokens & Context Window */}
          <div className="mdl-form-grid">
            <div>
              <label className="mdl-label">Max Tokens (output)</label>
              <Input
                type="number"
                value={formData.max_tokens}
                onChange={(e) => updateField('max_tokens', parseInt(e.target.value) || 0)}
                min={1}
                max={1000000}
              />
            </div>
            <div>
              <label className="mdl-label">Ventana de Contexto</label>
              <Input
                type="number"
                value={formData.context_window}
                onChange={(e) => updateField('context_window', parseInt(e.target.value) || 0)}
                min={1024}
                max={2000000}
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="mdl-label">Descripción</label>
            <textarea
              value={formData.description ?? ''}
              onChange={(e) => updateField('description', e.target.value)}
              className="mdl-textarea"
              rows={2}
              placeholder="Descripción del modelo y casos de uso..."
            />
          </div>

          {/* Active Status */}
          <div className="fi-flex-gap-md">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => updateField('is_active', e.target.checked)}
              className="mdl-active-checkbox"
            />
            <label htmlFor="is_active" className="fi-subtitle">
              Modelo activo (disponible para selección)
            </label>
          </div>

          {error && (
            <div className="mdl-form-error">{error}</div>
          )}

          <div className="mdl-form-actions">
            <Button type="button" onClick={onClose} variant="secondary" fullWidth>
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={saving}
              variant="primary"
              fullWidth
              loading={saving}
            >
              {mode === 'create' ? 'Crear Modelo' : 'Guardar Cambios'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
