'use client';

import { useCallback, useId } from 'react';
import { Cpu, Mic } from 'lucide-react';
import { FieldError, FieldLabel, OptionSelect } from './controls';
import { PERSONA_FIELD_CONSTRAINTS, type PersonaCreateFormValues, type PersonaFormValues } from './schema';
import type { PersonaHideableField, PersonaOption } from './types';
import { FI_PERSONA_ROOT_CLASS, usePersonaAdminStyle } from './personaAdminStyle';

export interface PersonaFormProps {
  value: PersonaFormValues;
  onChange: (values: PersonaFormValues) => void;
  /** 'create' adds the editable id field; 'edit' shows `personaId` read-only. */
  mode: 'create' | 'edit';
  modelOptions: readonly PersonaOption[];
  voiceOptions?: readonly PersonaOption[];
  hiddenFields?: readonly PersonaHideableField[];
  disabled?: boolean;
  errors?: Record<string, string>;
  personaId?: string;
  showSystemPrompt?: boolean;
  showExamplesSummary?: boolean;
  noVoiceLabel?: string;
}

export function generateIdFromName(name: string): string {
  return name
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9\s]/g, '')
    .trim()
    .replace(/\s+/g, '_')
    .replace(/^[^a-z]+/, '')
    .slice(0, PERSONA_FIELD_CONSTRAINTS.id.max);
}

function temperatureLabel(t: number): string {
  if (t < 0.3) return 'Determinístico';
  if (t < 0.7) return 'Balanceado';
  return 'Creativo';
}

export function PersonaForm({
  value,
  onChange,
  mode,
  modelOptions,
  voiceOptions = [],
  hiddenFields = [],
  disabled = false,
  errors = {},
  personaId,
  showSystemPrompt = true,
  showExamplesSummary = false,
  noVoiceLabel = 'Sin voz (Solo texto)',
}: PersonaFormProps) {
  usePersonaAdminStyle();
  const uid = useId();
  const fid = (name: string) => `${uid}-${name}`;
  const isCreate = mode === 'create';
  const form = value as Partial<PersonaCreateFormValues>;
  const hidden = new Set(hiddenFields);

  const set = useCallback(
    <K extends keyof PersonaCreateFormValues>(field: K, next: PersonaCreateFormValues[K]) => {
      onChange({ ...value, [field]: next } as PersonaFormValues);
    },
    [value, onChange],
  );

  const setName = useCallback(
    (name: string) => {
      if (!isCreate) return onChange({ ...value, name } as PersonaFormValues);
      const current = form.id ?? '';
      const derived = !current || current === generateIdFromName(form.name ?? '');
      onChange({ ...value, name, ...(derived ? { id: generateIdFromName(name) } : {}) } as PersonaFormValues);
    },
    [value, onChange, isCreate, form.id, form.name],
  );

  const invalid = (field: string) => (errors[field] ? true : undefined);
  const describedBy = (field: string) => (errors[field] ? fid(`${field}-error`) : undefined);
  const temperature = form.temperature ?? 0.7;

  return (
    <div className={`${FI_PERSONA_ROOT_CLASS} fi-persona-stack`}>
      <div className="fi-persona-grid">
        <div className="fi-persona-field">
          <FieldLabel htmlFor={fid('name')} required>
            Nombre
          </FieldLabel>
          <input
            id={fid('name')}
            className="fi-persona-input"
            type="text"
            value={form.name ?? ''}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ej: Asistente de Nutrición"
            disabled={disabled}
            maxLength={PERSONA_FIELD_CONSTRAINTS.name.max}
            aria-invalid={invalid('name')}
            aria-describedby={describedBy('name')}
          />
          <FieldError id={fid('name-error')} error={errors.name} />
        </div>
        <div className="fi-persona-field">
          <FieldLabel htmlFor={fid('id')} required={isCreate}>
            ID único
          </FieldLabel>
          <input
            id={fid('id')}
            className="fi-persona-input fi-persona-mono"
            type="text"
            value={isCreate ? (form.id ?? '') : (personaId ?? '')}
            onChange={(e) => set('id', e.target.value.toLowerCase())}
            placeholder="ej: nutrition_assistant"
            disabled={disabled || !isCreate}
            readOnly={!isCreate}
            maxLength={PERSONA_FIELD_CONSTRAINTS.id.max}
            aria-invalid={invalid('id')}
            aria-describedby={describedBy('id')}
          />
          <FieldError id={fid('id-error')} error={errors.id} />
        </div>
      </div>

      <div className="fi-persona-field">
        <FieldLabel htmlFor={fid('description')} required>
          Descripción
        </FieldLabel>
        <textarea
          id={fid('description')}
          className="fi-persona-input"
          rows={2}
          value={form.description ?? ''}
          onChange={(e) => set('description', e.target.value)}
          placeholder="Describe el propósito y comportamiento de esta persona..."
          disabled={disabled}
          maxLength={PERSONA_FIELD_CONSTRAINTS.description.max}
          aria-invalid={invalid('description')}
          aria-describedby={describedBy('description')}
        />
        <div className="fi-persona-hint">
          <FieldError id={fid('description-error')} error={errors.description} />
          <span>
            {(form.description ?? '').length}/{PERSONA_FIELD_CONSTRAINTS.description.max}
          </span>
        </div>
      </div>

      {showSystemPrompt ? (
        <div className="fi-persona-field">
          <FieldLabel htmlFor={fid('system_prompt')} required>
            System Prompt
          </FieldLabel>
          <textarea
            id={fid('system_prompt')}
            className="fi-persona-input fi-persona-mono"
            rows={5}
            value={form.system_prompt ?? ''}
            onChange={(e) => set('system_prompt', e.target.value)}
            placeholder="Eres un asistente especializado en..."
            disabled={disabled}
            maxLength={PERSONA_FIELD_CONSTRAINTS.system_prompt.max}
            aria-invalid={invalid('system_prompt')}
            aria-describedby={describedBy('system_prompt')}
          />
          <div className="fi-persona-hint">
            <FieldError id={fid('system_prompt-error')} error={errors.system_prompt} />
            <span>{(form.system_prompt ?? '').length} caracteres</span>
          </div>
        </div>
      ) : null}

      <div className="fi-persona-grid">
        <div className="fi-persona-field">
          <FieldLabel htmlFor={fid('model')} icon={Cpu}>
            Modelo
          </FieldLabel>
          <OptionSelect
            id={fid('model')}
            value={form.model ?? ''}
            options={modelOptions}
            onChange={(v) => set('model', v)}
            disabled={disabled}
            ariaInvalid={!!errors.model}
          />
          <FieldError error={errors.model} />
        </div>
        {hidden.has('voice') ? null : (
          <div className="fi-persona-field">
            <FieldLabel htmlFor={fid('voice')} icon={Mic}>
              Voz TTS
            </FieldLabel>
            <OptionSelect
              id={fid('voice')}
              value={form.voice ?? ''}
              options={voiceOptions}
              onChange={(v) => set('voice', v || null)}
              disabled={disabled}
              emptyLabel={noVoiceLabel}
            />
            <FieldError error={errors.voice} />
          </div>
        )}
      </div>

      {hidden.has('temperature') && hidden.has('max_tokens') ? null : (
        <div className="fi-persona-grid">
          {hidden.has('temperature') ? null : (
            <div className="fi-persona-field">
              <FieldLabel htmlFor={fid('temperature')}>
                Temperatura: {temperature.toFixed(2)} ({temperatureLabel(temperature)})
              </FieldLabel>
              <input
                id={fid('temperature')}
                className="fi-persona-range"
                type="range"
                min={PERSONA_FIELD_CONSTRAINTS.temperature.min}
                max={PERSONA_FIELD_CONSTRAINTS.temperature.max}
                step={PERSONA_FIELD_CONSTRAINTS.temperature.step}
                value={temperature}
                onChange={(e) => set('temperature', parseFloat(e.target.value))}
                disabled={disabled}
              />
              <div className="fi-persona-hint">
                <span>Preciso</span>
                <span>Creativo</span>
              </div>
              <FieldError error={errors.temperature} />
            </div>
          )}
          {hidden.has('max_tokens') ? null : (
            <div className="fi-persona-field">
              <FieldLabel htmlFor={fid('max_tokens')}>Max tokens</FieldLabel>
              <input
                id={fid('max_tokens')}
                className="fi-persona-input"
                type="number"
                inputMode="numeric"
                min={PERSONA_FIELD_CONSTRAINTS.max_tokens.min}
                max={PERSONA_FIELD_CONSTRAINTS.max_tokens.max}
                step={PERSONA_FIELD_CONSTRAINTS.max_tokens.step}
                value={form.max_tokens ?? 2048}
                onChange={(e) => set('max_tokens', parseInt(e.target.value, 10) || 0)}
                disabled={disabled}
                aria-invalid={invalid('max_tokens')}
              />
              <FieldError error={errors.max_tokens} />
            </div>
          )}
        </div>
      )}

      {showExamplesSummary && !hidden.has('examples') && (form.examples?.length ?? 0) > 0 ? (
        <p className="fi-persona-hint">{form.examples?.length} ejemplo(s) configurado(s)</p>
      ) : null}
    </div>
  );
}
