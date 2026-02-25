/**
 * ContentManagement - Unified Content CRUD Interface
 *
 * Manages all TV content types:
 * - FI Seeds (editable defaults)
 * - Trivia Questions
 * - Breathing Exercises
 * - Daily Tips
 * - Doctor Media (images/videos/messages)
 *
 * Card: FI-TV-REFAC-003
 */

'use client';

import { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Sparkles, Home, Brain, Activity, Lightbulb } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TriviaEditor } from './TriviaEditor';
import { getTriviaQuestions, type TriviaQuestion } from '@/lib/api/widget-configs';
import { toastSuccess, toastError } from '@/lib/swal';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('ContentManagement');

type ContentTab = 'seeds' | 'trivias' | 'exercises' | 'tips';

interface ContentManagementProps {
  onRefresh?: () => void;
}

export function ContentManagement({ onRefresh }: ContentManagementProps) {
  const [activeTab, setActiveTab] = useState<ContentTab>('trivias');
  const [showTriviaEditor, setShowTriviaEditor] = useState(false);
  const [editingTrivia, setEditingTrivia] = useState<TriviaQuestion | undefined>();
  const [trivias, setTrivias] = useState<TriviaQuestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Load trivias on mount
  useEffect(() => {
    if (activeTab === 'trivias') {
      loadTrivias();
    }
  }, [activeTab]);

  const loadTrivias = async () => {
    setIsLoading(true);
    try {
      const response = await getTriviaQuestions();
      setTrivias(response.questions);
    } catch (error) {
      log.error('Failed to load trivias', { error: String(error) });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveTrivia = async (trivia: TriviaQuestion) => {
    try {
      setShowTriviaEditor(false);
      setEditingTrivia(undefined);
      await loadTrivias();
      onRefresh?.();

      toastSuccess('Trivia guardada');
    } catch (error) {
      log.error('Failed to save trivia', { error: String(error) });
      toastError('Error al guardar trivia');
    }
  };

  const tabs: { id: ContentTab; label: string; icon: LucideIcon; count: number }[] = [
    { id: 'seeds', label: 'Contenido FI', icon: Home, count: 13 },
    { id: 'trivias', label: 'Trivias', icon: Brain, count: trivias.length },
    { id: 'exercises', label: 'Ejercicios', icon: Activity, count: 3 },
    { id: 'tips', label: 'Tips', icon: Lightbulb, count: 12 },
  ];

  return (
    <div className="cmgt-wrap">
      {/* Tabs */}
      <div className="cmgt-tabs-row">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={activeTab === tab.id ? 'fi-tab-gradient-active' : 'fi-tab-gradient'}
            variant={activeTab === tab.id ? 'primary' : 'ghost'}
            size="sm"
            type="button"
          >
            <tab.icon className="cmgt-tab-icon" />
            <span>{tab.label}</span>
            <span
              className={`fi-count-badge ${activeTab === tab.id ? 'cmgt-tab-count-active' : 'cmgt-tab-count'}`}
            >
              {tab.count}
            </span>
          </Button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="cmgt-content-area">
        {/* Seeds Tab */}
        {activeTab === 'seeds' && (
          <div className="fi-empty-state">
            <Sparkles className="cmgt-empty-icon fi-text-purple" />
            <h3 className="fi-title-xl cmgt-empty-title">Contenido FI</h3>
            <p className="cmgt-empty-desc">
              13 seeds editables (mensajes de bienvenida, filosofía, tips básicos)
            </p>
            <p className="fi-text-muted">
              Gestión de seeds FI disponible próximamente
            </p>
          </div>
        )}

        {/* Trivias Tab */}
        {activeTab === 'trivias' && (
          <div>
            {/* Header */}
            <div className="cmgt-trivia-header">
              <div>
                <h3 className="cmgt-trivia-title">Trivias de Salud</h3>
                <p className="fi-subtitle">
                  Preguntas educativas para pacientes en sala de espera
                </p>
              </div>
              <Button
                onClick={() => {
                  setEditingTrivia(undefined);
                  setShowTriviaEditor(true);
                }}
                className="fi-btn-cta-icon"
                variant="primary"
                size="sm"
                type="button"
              >
                <Plus className="cmgt-btn-icon" />
                Nueva Trivia
              </Button>
            </div>

            {/* Trivias List */}
            {isLoading ? (
              <div className="fi-empty-state">
                <div className="cmgt-spinner"></div>
                <p className="cmgt-spinner-text">Cargando trivias...</p>
              </div>
            ) : trivias.length === 0 ? (
              <div className="fi-empty-state">
                <p className="cmgt-empty-text">No hay trivias configuradas</p>
                <p className="cmgt-empty-hint">
                  Haz click en &quot;Nueva Trivia&quot; para crear una
                </p>
              </div>
            ) : (
              <div className="fi-stack-md">
                {trivias.map((trivia, index) => (
                  <div
                    key={trivia.id}
                    className="cmgt-trivia-card"
                  >
                    <div className="cmgt-trivia-row">
                      {/* Number Badge */}
                      <div className="cmgt-trivia-badge">
                        <span className="cmgt-trivia-badge-text">{index + 1}</span>
                      </div>

                      {/* Content */}
                      <div className="cmgt-trivia-body">
                        <div className="cmgt-trivia-title-row">
                          <h4 className="cmgt-trivia-question">
                            {trivia.question}
                          </h4>
                          <div className="fi-flex-gap">
                            {/* Difficulty Badge */}
                            <span
                              className={trivia.difficulty === 'easy' ? 'fi-difficulty-easy' : trivia.difficulty === 'medium' ? 'fi-difficulty-medium' : 'fi-difficulty-hard'}
                            >
                              {trivia.difficulty === 'easy'
                                ? 'Fácil'
                                : trivia.difficulty === 'medium'
                                ? 'Media'
                                : 'Difícil'}
                            </span>

                            {/* Category */}
                            <span className="cmgt-category-badge fi-text-xs-medium fi-text">
                              {trivia.category}
                            </span>
                          </div>
                        </div>

                        {/* Options Preview */}
                        <div className="cmgt-options-grid">
                          {trivia.options.slice(0, 4).map((option, i) => (
                            <div
                              key={i}
                              className={i === trivia.correct ? 'fi-answer-option-correct' : 'fi-answer-option'}
                            >
                              {String.fromCharCode(65 + i)}. {option}
                            </div>
                          ))}
                        </div>

                        {/* Tags */}
                        {trivia.tags.length > 0 && (
                          <div className="cmgt-tags-row">
                            {trivia.tags.map((tag) => (
                              <span
                                key={tag}
                                className="cmgt-tag"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="fi-flex-gap">
                        <Button
                          type="button"
                          onClick={() => {
                            setEditingTrivia(trivia);
                            setShowTriviaEditor(true);
                          }}
                          className="cmgt-edit-btn fi-text-primary"
                          title="Editar"
                          variant="ghost"
                          size="sm"
                        >
                          <Edit className="cmgt-btn-icon" />
                        </Button>
                        <Button
                          type="button"
                          className="cmgt-delete-btn fi-text-error"
                          title="Eliminar (próximamente)"
                          disabled
                          variant="ghost"
                          size="sm"
                        >
                          <Trash2 className="cmgt-btn-icon" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Exercises Tab */}
        {activeTab === 'exercises' && (
          <div className="fi-empty-state">
            <Activity className="cmgt-empty-icon fi-text-purple" />
            <h3 className="fi-title-xl cmgt-empty-title">Ejercicios de Respiración</h3>
            <p className="cmgt-empty-desc">3 ejercicios configurados (Box, 4-7-8, Coherent)</p>
            <p className="fi-text-muted">Editor de ejercicios disponible próximamente</p>
          </div>
        )}

        {/* Tips Tab */}
        {activeTab === 'tips' && (
          <div className="fi-empty-state">
            <Lightbulb className="cmgt-empty-icon fi-text-purple" />
            <h3 className="fi-title-xl cmgt-empty-title">Tips de Salud</h3>
            <p className="cmgt-empty-desc">
              12 tips en 4 categorías (nutrición, ejercicio, salud mental, prevención)
            </p>
            <p className="fi-text-muted">Editor de tips disponible próximamente</p>
          </div>
        )}
      </div>

      {/* Trivia Editor Modal */}
      {showTriviaEditor && (
        <TriviaEditor
          question={editingTrivia}
          onSave={handleSaveTrivia}
          onCancel={() => {
            setShowTriviaEditor(false);
            setEditingTrivia(undefined);
          }}
        />
      )}
    </div>
  );
}
