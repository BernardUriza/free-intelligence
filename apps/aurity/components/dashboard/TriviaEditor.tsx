/**
 * TriviaEditor - CRUD Interface for Health Trivia Questions
 *
 * Allows doctors to create/edit trivia questions for waiting room TV.
 * Integrates with backend widget-config API.
 *
 * Card: FI-TV-REFAC-003
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { X, Plus, Trash2, Save, AlertCircle, Brain } from 'lucide-react';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('TriviaEditor');

interface TriviaQuestion {
  id: string;
  question: string;
  options: string[];
  correct: number;
  explanation: string;
  difficulty: 'easy' | 'medium' | 'hard';
  category: string;
  tags: string[];
}

interface TriviaEditorProps {
  question?: TriviaQuestion; // For editing existing
  onSave: (question: TriviaQuestion) => Promise<void>;
  onCancel: () => void;
}

export function TriviaEditor({ question, onSave, onCancel }: TriviaEditorProps) {
  const [formData, setFormData] = useState<TriviaQuestion>(
    question || {
      id: '',
      question: '',
      options: ['', '', '', ''],
      correct: 0,
      explanation: '',
      difficulty: 'medium',
      category: '',
      tags: [],
    }
  );

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [tagInput, setTagInput] = useState('');

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (formData.question.length < 10) {
      newErrors.question = 'La pregunta debe tener al menos 10 caracteres';
    }

    const validOptions = formData.options.filter(opt => opt.trim().length > 0);
    if (validOptions.length < 2) {
      newErrors.options = 'Debe haber al menos 2 opciones';
    }

    if (formData.explanation.length < 10) {
      newErrors.explanation = 'La explicación debe tener al menos 10 caracteres';
    }

    if (!formData.category.trim()) {
      newErrors.category = 'La categoría es requerida';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) return;

    setIsSaving(true);
    try {
      // Generate ID if creating new
      if (!formData.id) {
        formData.id = `${formData.category}-${Date.now()}`;
      }

      await onSave(formData);
    } catch (error) {
      log.error('Failed to save trivia', { error: String(error) });
      setErrors({ general: 'Error al guardar. Intente nuevamente.' });
    } finally {
      setIsSaving(false);
    }
  };

  const addOption = () => {
    if (formData.options.length < 6) {
      setFormData({
        ...formData,
        options: [...formData.options, ''],
      });
    }
  };

  const removeOption = (index: number) => {
    if (formData.options.length > 2) {
      const newOptions = formData.options.filter((_, i) => i !== index);
      setFormData({
        ...formData,
        options: newOptions,
        correct: formData.correct >= newOptions.length ? 0 : formData.correct,
      });
    }
  };

  const updateOption = (index: number, value: string) => {
    const newOptions = [...formData.options];
    newOptions[index] = value;
    setFormData({ ...formData, options: newOptions });
  };

  const addTag = () => {
    if (tagInput.trim() && !formData.tags.includes(tagInput.trim())) {
      setFormData({
        ...formData,
        tags: [...formData.tags, tagInput.trim()],
      });
      setTagInput('');
    }
  };

  const removeTag = (tag: string) => {
    setFormData({
      ...formData,
      tags: formData.tags.filter(t => t !== tag),
    });
  };

  return (
    <div className="fi-modal-backdrop">
      <div className="triv-modal">
        {/* Header */}
        <div className="triv-header">
          <div className="fi-flex-between">
            <div className="fi-flex-gap-md">
              <Brain className="triv-header-icon" strokeWidth={1.5} aria-hidden="true" />
              <h2 className="fi-title-2xl">
                {question ? 'Editar Trivia' : 'Nueva Trivia'}
              </h2>
            </div>
            <Button
              onClick={onCancel}
              variant="ghost"
              size="sm"
              icon={X}
              aria-label="Cerrar"
            />
          </div>
        </div>

        {/* Form */}
        <div className="triv-form">
          {/* Error Banner */}
          {errors.general && (
            <div className="triv-error-banner">
              <AlertCircle className="triv-error-icon fi-text-error" />
              <p className="triv-error-text">{errors.general}</p>
            </div>
          )}

          {/* Question */}
          <div>
            <label className="triv-label">
              Pregunta *
            </label>
            <textarea
              value={formData.question}
              onChange={(e) => setFormData({ ...formData, question: e.target.value })}
              className="fi-textarea-ghost"
              rows={3}
              placeholder="¿Cuántos vasos de agua se recomienda beber al día?"
            />
            {errors.question && (
              <p className="triv-field-error fi-text-error">{errors.question}</p>
            )}
          </div>

          {/* Options */}
          <div>
            <div className="triv-options-header">
              <label className="triv-options-label">
                Opciones * (mínimo 2, máximo 6)
              </label>
              <Button
                onClick={addOption}
                disabled={formData.options.length >= 6}
                variant="outline"
                size="sm"
                icon={Plus}
                className="triv-add-option-btn"
              >
                Agregar opción
              </Button>
            </div>

            <div className="triv-options-list">
              {formData.options.map((option, index) => (
                <div key={index} className="fi-flex-gap">
                  <input
                    type="radio"
                    checked={formData.correct === index}
                    onChange={() => setFormData({ ...formData, correct: index })}
                    className="triv-radio"
                  />
                  <input
                    type="text"
                    value={option}
                    onChange={(e) => updateOption(index, e.target.value)}
                    className="fi-input-ghost flex-1"
                    placeholder={`Opción ${String.fromCharCode(65 + index)}`}
                  />
                  {formData.options.length > 2 && (
                    <Button
                      onClick={() => removeOption(index)}
                      variant="ghost"
                      size="sm"
                      icon={Trash2}
                      className="fi-text-error triv-remove-option"
                      aria-label="Eliminar opción"
                    />
                  )}
                </div>
              ))}
            </div>
            {errors.options && (
              <p className="triv-field-error fi-text-error">{errors.options}</p>
            )}
          </div>

          {/* Explanation */}
          <div>
            <label className="triv-label">
              Explicación de la Respuesta Correcta *
            </label>
            <textarea
              value={formData.explanation}
              onChange={(e) => setFormData({ ...formData, explanation: e.target.value })}
              className="fi-textarea-ghost"
              rows={3}
              placeholder="Se recomienda beber entre 8 y 10 vasos al día..."
            />
            {errors.explanation && (
              <p className="triv-field-error fi-text-error">{errors.explanation}</p>
            )}
          </div>

          {/* Metadata Row */}
          <div className="triv-metadata-grid">
            {/* Difficulty */}
            <div>
              <label className="triv-label">
                Dificultad
              </label>
              <Select value={formData.difficulty} onValueChange={(val) => setFormData({ ...formData, difficulty: val as TriviaQuestion['difficulty'] })}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Seleccionar dificultad" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="easy">Fácil</SelectItem>
                  <SelectItem value="medium">Media</SelectItem>
                  <SelectItem value="hard">Difícil</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Category */}
            <div>
              <label className="triv-label">
                Categoría *
              </label>
              <input
                type="text"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="fi-input-ghost"
                placeholder="hydration, exercise..."
              />
              {errors.category && (
                <p className="triv-field-error fi-text-error">{errors.category}</p>
              )}
            </div>

            {/* Tags */}
            <div>
              <label className="triv-label">
                Tags
              </label>
              <div className="triv-tags-input-row">
                <input
                  type="text"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
                  className="fi-input-ghost flex-1"
                  placeholder="agua, salud..."
                />
                <Button
                  onClick={addTag}
                  variant="ghost"
                  size="sm"
                  icon={Plus}
                  className="triv-add-tag-btn"
                  aria-label="Agregar tag"
                />
              </div>
            </div>
          </div>

          {/* Tags Display */}
          {formData.tags.length > 0 && (
            <div className="triv-tags-display">
              {formData.tags.map((tag) => (
                <span
                  key={tag}
                  className="triv-tag"
                >
                  {tag}
                  <Button
                    onClick={() => removeTag(tag)}
                    variant="ghost"
                    size="sm"
                    icon={X}
                    className="triv-remove-tag hover:fi-text-error"
                    aria-label="Eliminar tag"
                  />
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="triv-footer fi-border-top">
          <Button variant="secondary" onClick={onCancel}>
            Cancelar
          </Button>
          <Button
            onClick={handleSave}
            disabled={isSaving}
            loading={isSaving}
            icon={Save}
          >
            {isSaving ? 'Guardando...' : 'Guardar Trivia'}
          </Button>
        </div>
      </div>
    </div>
  );
}
