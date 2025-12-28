/**
 * PersonaForm Component
 *
 * Reusable, controlled form for creating/editing Personas.
 * Single Responsibility: Pure UI + validation display, no network calls.
 * Dependency Inversion: Receives handlers via props.
 *
 * @module components/admin/persona/PersonaForm
 */

'use client';

import { useCallback } from 'react';
import { AlertCircle } from 'lucide-react';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import type { PersonaFormProps, PersonaCreateFormValues, PersonaFormValues } from './types';
import { VOICE_OPTIONS, MODEL_OPTIONS } from './types';
import { PERSONA_FIELD_CONSTRAINTS } from './schema';

/**
 * Generate ID from name (lowercase, underscores)
 */
function generateIdFromName(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, '')
    .replace(/\s+/g, '_')
    .slice(0, 64);
}

/**
 * Field error display component
 */
function FieldError({ error }: { error?: string }) {
  if (!error) return null;
  return (
    <p className="mt-1 text-xs fi-text-error flex items-center gap-1" role="alert">
      <AlertCircle className="fi-icon-xs" />
      {error}
    </p>
  );
}

/**
 * Form field label component
 */
function FieldLabel({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label className="fi-label">
      {children}
      {required && <span className="fi-text-error ml-1">*</span>}
    </label>
  );
}

/**
 * PersonaForm - Controlled form component
 *
 * Pure UI component that renders form fields and validation errors.
 * Does NOT make any API calls - all persistence is handled by parent.
 */
export function PersonaForm({
  value,
  onChange,
  disabled = false,
  errors = {},
  mode,
  showAdvanced = false,
}: PersonaFormProps) {
  // Type guard for create mode
  const isCreateMode = mode === 'create';
  const formValue = value as PersonaCreateFormValues;

  // Generic field change handler
  const handleChange = useCallback(
    <K extends keyof PersonaCreateFormValues>(field: K, fieldValue: PersonaCreateFormValues[K]) => {
      onChange({ ...value, [field]: fieldValue } as PersonaFormValues);
    },
    [value, onChange]
  );

  // Handle name change with auto-ID generation in create mode
  const handleNameChange = useCallback(
    (name: string) => {
      if (isCreateMode) {
        const currentId = (value as PersonaCreateFormValues).id;
        // Only auto-generate if ID is empty or was auto-generated
        const shouldAutoGenerate = !currentId || currentId === generateIdFromName((value as PersonaCreateFormValues).name || '');
        onChange({
          ...value,
          name,
          ...(shouldAutoGenerate ? { id: generateIdFromName(name) } : {}),
        } as PersonaFormValues);
      } else {
        onChange({ ...value, name } as PersonaFormValues);
      }
    },
    [value, onChange, isCreateMode]
  );

  return (
    <div className="space-y-5">
      {/* Name & ID Row (ID only in create mode) */}
      <div className={`grid gap-4 ${isCreateMode ? 'grid-cols-2' : 'grid-cols-1'}`}>
        {/* Name */}
        <div>
          <FieldLabel required>Nombre</FieldLabel>
          <input
            type="text"
            value={formValue.name || ''}
            onChange={(e) => handleNameChange(e.target.value)}
            placeholder="Ej: Asistente de Nutrición"
            disabled={disabled}
            maxLength={PERSONA_FIELD_CONSTRAINTS.name.max}
            className={`w-full p-3 bg-slate-800 border rounded-lg text-white placeholder-slate-500 focus:outline-none transition-colors ${
              errors.name
                ? 'border-red-500 focus:border-red-500'
                : 'border-slate-700 focus:border-purple-500'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            aria-invalid={!!errors.name}
            aria-describedby={errors.name ? 'name-error' : undefined}
          />
          <FieldError error={errors.name} />
        </div>

        {/* ID (only in create mode) */}
        {isCreateMode && (
          <div>
            <FieldLabel required>ID Único</FieldLabel>
            <input
              type="text"
              value={formValue.id || ''}
              onChange={(e) => handleChange('id', e.target.value.toLowerCase())}
              placeholder="ej: nutrition_assistant"
              disabled={disabled}
              maxLength={PERSONA_FIELD_CONSTRAINTS.id.max}
              className={`w-full p-3 bg-slate-800 border rounded-lg text-white font-mono text-sm placeholder-slate-500 focus:outline-none transition-colors ${
                errors.id
                  ? 'border-red-500 focus:border-red-500'
                  : 'border-slate-700 focus:border-purple-500'
              } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
              aria-invalid={!!errors.id}
              aria-describedby={errors.id ? 'id-error' : undefined}
            />
            <FieldError error={errors.id} />
          </div>
        )}
      </div>

      {/* Description */}
      <div>
        <FieldLabel required>Descripción</FieldLabel>
        <textarea
          value={formValue.description || ''}
          onChange={(e) => handleChange('description', e.target.value)}
          placeholder="Describe el propósito y comportamiento de esta persona..."
          disabled={disabled}
          rows={2}
          maxLength={PERSONA_FIELD_CONSTRAINTS.description.max}
          className={`w-full p-3 bg-slate-800 border rounded-lg text-white placeholder-slate-500 focus:outline-none resize-none transition-colors ${
            errors.description
              ? 'border-red-500 focus:border-red-500'
              : 'border-slate-700 focus:border-purple-500'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          aria-invalid={!!errors.description}
        />
        <div className="flex justify-between mt-1">
          <FieldError error={errors.description} />
          <span className="fi-text-xs-muted">
            {(formValue.description || '').length}/{PERSONA_FIELD_CONSTRAINTS.description.max}
          </span>
        </div>
      </div>

      {/* System Prompt */}
      <div>
        <FieldLabel required>System Prompt</FieldLabel>
        <textarea
          value={formValue.system_prompt || ''}
          onChange={(e) => handleChange('system_prompt', e.target.value)}
          placeholder="Eres un asistente especializado en..."
          disabled={disabled}
          rows={5}
          maxLength={PERSONA_FIELD_CONSTRAINTS.system_prompt.max}
          className={`w-full p-3 bg-slate-800 border rounded-lg text-white font-mono text-sm placeholder-slate-500 focus:outline-none resize-none transition-colors ${
            errors.system_prompt
              ? 'border-red-500 focus:border-red-500'
              : 'border-slate-700 focus:border-purple-500'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          aria-invalid={!!errors.system_prompt}
        />
        <div className="flex justify-between mt-1">
          <FieldError error={errors.system_prompt} />
          <span className="fi-text-xs-muted">
            {(formValue.system_prompt || '').length} caracteres
          </span>
        </div>
      </div>

      {/* Model & Voice Row */}
      <div className="fi-grid-2">
        {/* Model */}
        <div>
          <FieldLabel>Modelo LLM</FieldLabel>
          <Select
            value={formValue.model || 'qwen3:1.7b'}
            onValueChange={(val) => handleChange('model', val)}
            disabled={disabled}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Seleccionar modelo" />
            </SelectTrigger>
            <SelectContent>
              {MODEL_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FieldError error={errors.model} />
        </div>

        {/* Voice */}
        <div>
          <FieldLabel>Voz TTS</FieldLabel>
          <Select
            value={formValue.voice || 'nova'}
            onValueChange={(val) => handleChange('voice', val)}
            disabled={disabled}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Seleccionar voz" />
            </SelectTrigger>
            <SelectContent>
              {VOICE_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FieldError error={errors.voice} />
        </div>
      </div>

      {/* Temperature & Max Tokens Row */}
      <div className="fi-grid-2">
        {/* Temperature */}
        <div>
          <FieldLabel>
            Temperatura: {(formValue.temperature ?? 0.7).toFixed(1)}
          </FieldLabel>
          <input
            type="range"
            min={PERSONA_FIELD_CONSTRAINTS.temperature.min}
            max={PERSONA_FIELD_CONSTRAINTS.temperature.max}
            step={PERSONA_FIELD_CONSTRAINTS.temperature.step}
            value={formValue.temperature ?? 0.7}
            onChange={(e) => handleChange('temperature', parseFloat(e.target.value))}
            disabled={disabled}
            className={`w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-500 ${
              disabled ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          />
          <div className="flex justify-between fi-text-xs-muted mt-1">
            <span>Preciso</span>
            <span>Creativo</span>
          </div>
          <FieldError error={errors.temperature} />
        </div>

        {/* Max Tokens */}
        <div>
          <FieldLabel>Max Tokens</FieldLabel>
          <input
            type="number"
            min={PERSONA_FIELD_CONSTRAINTS.max_tokens.min}
            max={PERSONA_FIELD_CONSTRAINTS.max_tokens.max}
            step={PERSONA_FIELD_CONSTRAINTS.max_tokens.step}
            value={formValue.max_tokens ?? 2048}
            onChange={(e) => handleChange('max_tokens', parseInt(e.target.value) || 2048)}
            disabled={disabled}
            className={`w-full p-3 fi-panel text-white focus:border-purple-500 focus:outline-none transition-colors ${
              disabled ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          />
          <FieldError error={errors.max_tokens} />
        </div>
      </div>

      {/* Advanced: Examples (optional) */}
      {showAdvanced && formValue.examples && formValue.examples.length > 0 && (
        <div>
          <FieldLabel>Examples ({formValue.examples.length})</FieldLabel>
          <div className="p-3 fi-panel">
            <p className="fi-subtitle">
              {formValue.examples.length} ejemplo(s) configurado(s)
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default PersonaForm;
