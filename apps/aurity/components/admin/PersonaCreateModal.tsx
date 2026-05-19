/**
 * PersonaCreateModal Component
 *
 * Modal for creating new AI personas (FI-superadmin only).
 * Validates inputs and creates persona via API.
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { createLogger } from '@/lib/internal/logger';
import {
  X,
  AlertCircle,
  Sparkles,
} from 'lucide-react';

const log = createLogger('PersonaCreate');
import type { Persona, PersonaCreateRequest } from '@aurity-standalone/types/persona';
import { createPersona } from '@aurity-standalone/api-client/personas';

interface PersonaCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (persona: Persona) => void;
  // Note: authToken removed - now handled automatically by api client
}

// Available TTS voices
const VOICE_OPTIONS = [
  { value: 'nova', label: 'Nova (Cálida, femenina)' },
  { value: 'shimmer', label: 'Shimmer (Clara, femenina)' },
  { value: 'alloy', label: 'Alloy (Neutral)' },
  { value: 'echo', label: 'Echo (Profunda, masculina)' },
  { value: 'fable', label: 'Fable (Narrativa)' },
  { value: 'onyx', label: 'Onyx (Grave, masculina)' },
];

// Default LLM models
const MODEL_OPTIONS = [
  { value: 'qwen3:1.7b', label: 'Qwen3 1.7B (Local, rápido)' },
  { value: 'qwen3:8b', label: 'Qwen3 8B (Local, balanced)' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (Cloud, económico)' },
  { value: 'gpt-4o', label: 'GPT-4o (Cloud, preciso)' },
  { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet (Cloud)' },
];

export function PersonaCreateModal({
  isOpen,
  onClose,
  onSuccess,
}: PersonaCreateModalProps) {
  // Form state
  const [formData, setFormData] = useState<PersonaCreateRequest>({
    id: '',
    name: '',
    description: '',
    system_prompt: '',
    model: 'qwen3:1.7b',
    voice: 'nova',
    temperature: 0.7,
    max_tokens: 2048,
    examples: [],
  });

  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // Generate ID from name
  const generateId = (name: string): string => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .replace(/\s+/g, '_')
      .slice(0, 64);
  };

  // Handle name change and auto-generate ID
  const handleNameChange = (name: string) => {
    setFormData((prev) => ({
      ...prev,
      name,
      id: prev.id || generateId(name), // Only auto-generate if ID is empty
    }));
  };

  // Validate form
  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.id) {
      errors.id = 'El ID es requerido';
    } else if (!/^[a-z][a-z0-9_]*$/.test(formData.id)) {
      errors.id = 'El ID debe empezar con letra minúscula y solo contener letras, números y guiones bajos';
    }

    if (!formData.name || formData.name.length < 1) {
      errors.name = 'El nombre es requerido';
    }

    if (!formData.description || formData.description.length < 10) {
      errors.description = 'La descripción debe tener al menos 10 caracteres';
    }

    if (!formData.system_prompt || formData.system_prompt.length < 20) {
      errors.system_prompt = 'El prompt del sistema debe tener al menos 20 caracteres';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle form submission
  const handleCreate = async () => {
    if (!validate()) return;

    try {
      setCreating(true);
      setError(null);

      // authToken is now handled automatically by api client
      const persona = await createPersona(formData);
      onSuccess(persona);
      handleClose();
    } catch (err) {
      log.error('Failed to create persona', { error: String(err) });
      setError(err instanceof Error ? err.message : 'Error al crear la persona');
    } finally {
      setCreating(false);
    }
  };

  // Reset and close
  const handleClose = () => {
    if (creating) return;
    setFormData({
      id: '',
      name: '',
      description: '',
      system_prompt: '',
      model: 'qwen3:1.7b',
      voice: 'nova',
      temperature: 0.7,
      max_tokens: 2048,
      examples: [],
    });
    setError(null);
    setValidationErrors({});
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative flex min-h-full items-center justify-center p-4">
        <div className="fi-modal-md max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="fi-modal-header flex-shrink-0">
            <div className="fi-flex-gap">
              <div className="p-2 rounded-lg bg-purple-900 border border-purple-700">
                <Sparkles className="w-5 h-5 fi-text-purple" />
              </div>
              <div>
                <h2 className="fi-title-xl">Crear Nueva Persona</h2>
                <p className="fi-subtitle">Define una nueva personalidad de IA</p>
              </div>
            </div>
            <button
              onClick={handleClose}
              disabled={creating}
              className="fi-btn-icon disabled:opacity-50"
            >
              <X className="w-5 h-5 text-slate-400" />
            </button>
          </div>

          {/* Content - Scrollable */}
          <div className="p-6 space-y-5 overflow-y-auto flex-1">
            {/* Name & ID Row */}
            <div className="fi-grid-2">
              {/* Name */}
              <div>
                <label className="fi-label">
                  Nombre <span className="fi-text-error">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleNameChange(e.target.value)}
                  placeholder="Ej: Asistente de Nutrición"
                  className={`fi-input-purple ${validationErrors.name ? 'fi-input-error' : ''}`}
                />
                {validationErrors.name && (
                  <p className="fi-input-error-message">{validationErrors.name}</p>
                )}
              </div>

              {/* ID */}
              <div>
                <label className="fi-label">
                  ID Único <span className="fi-text-error">*</span>
                </label>
                <input
                  type="text"
                  value={formData.id}
                  onChange={(e) => setFormData((prev) => ({ ...prev, id: e.target.value.toLowerCase() }))}
                  placeholder="ej: nutrition_assistant"
                  className={`fi-input-purple font-mono text-sm ${validationErrors.id ? 'fi-input-error' : ''}`}
                />
                {validationErrors.id && (
                  <p className="fi-input-error-message">{validationErrors.id}</p>
                )}
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="fi-label">
                Descripción <span className="fi-text-error">*</span>
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="Describe el propósito y comportamiento de esta persona..."
                rows={2}
                className={`fi-input-purple resize-none ${validationErrors.description ? 'fi-input-error' : ''}`}
              />
              {validationErrors.description && (
                <p className="fi-input-error-message">{validationErrors.description}</p>
              )}
            </div>

            {/* System Prompt */}
            <div>
              <label className="fi-label">
                System Prompt <span className="fi-text-error">*</span>
              </label>
              <textarea
                value={formData.system_prompt}
                onChange={(e) => setFormData((prev) => ({ ...prev, system_prompt: e.target.value }))}
                placeholder="Eres un asistente especializado en..."
                rows={5}
                className={`fi-input-purple font-mono text-sm resize-none ${validationErrors.system_prompt ? 'fi-input-error' : ''}`}
              />
              <div className="flex justify-between mt-1">
                {validationErrors.system_prompt ? (
                  <p className="text-xs fi-text-error">{validationErrors.system_prompt}</p>
                ) : (
                  <span />
                )}
                <p className="fi-text-xs-muted">
                  {formData.system_prompt.length} caracteres
                </p>
              </div>
            </div>

            {/* Model & Voice Row */}
            <div className="fi-grid-2">
              {/* Model */}
              <div>
                <label className="fi-label">Modelo LLM</label>
                <Select value={formData.model} onValueChange={(val) => setFormData((prev) => ({ ...prev, model: val }))}>
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
              </div>

              {/* Voice */}
              <div>
                <label className="fi-label">Voz TTS</label>
                <Select value={formData.voice || 'nova'} onValueChange={(val) => setFormData((prev) => ({ ...prev, voice: val }))}>
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
              </div>
            </div>

            {/* Temperature & Max Tokens Row */}
            <div className="fi-grid-2">
              {/* Temperature */}
              <div>
                <label className="fi-label">
                  Temperatura: {formData.temperature?.toFixed(1)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.temperature}
                  onChange={(e) => setFormData((prev) => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                  className="admin-range-input"
                />
                <div className="fi-flex-between fi-text-xs-muted mt-1">
                  <span>Preciso</span>
                  <span>Creativo</span>
                </div>
              </div>

              {/* Max Tokens */}
              <div>
                <label className="fi-label">Max Tokens</label>
                <input
                  type="number"
                  min="256"
                  max="8192"
                  step="256"
                  value={formData.max_tokens}
                  onChange={(e) => setFormData((prev) => ({ ...prev, max_tokens: parseInt(e.target.value) || 2048 }))}
                  className="fi-input-purple"
                />
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-900/20 border border-red-800 rounded-lg">
                <AlertCircle className="w-5 h-5 fi-text-error flex-shrink-0" />
                <p className="text-sm text-red-300">{error}</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="fi-modal-footer fi-flex-between flex-shrink-0">
            <p className="fi-text-muted">
              <span className="fi-text-error">*</span> Campos requeridos
            </p>
            <div className="fi-flex-gap">
              <Button onClick={handleClose} disabled={creating} variant="secondary">
                Cancelar
              </Button>
              <Button
                onClick={handleCreate}
                disabled={creating}
                variant="primary"
                icon={creating ? undefined : Sparkles}
                loading={creating}
              >
                {creating ? 'Creando...' : 'Crear Persona'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
