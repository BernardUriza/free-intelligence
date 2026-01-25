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
      console.error('Failed to load trivias:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveTrivia = async (trivia: TriviaQuestion) => {
    try {
      // TODO: Implement backend POST endpoint for saving
      console.log('Saving trivia:', trivia);

      // For now, just update the JSON file manually
      // In production, this would call saveTriviaQuestion(trivia)

      setShowTriviaEditor(false);
      setEditingTrivia(undefined);
      await loadTrivias();
      onRefresh?.();

      toastSuccess('Trivia guardada');
    } catch (error) {
      console.error('Failed to save trivia:', error);
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
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex gap-2 overflow-x-auto pb-2">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={activeTab === tab.id ? 'fi-tab-gradient-active' : 'fi-tab-gradient'}
            variant={activeTab === tab.id ? 'primary' : 'ghost'}
            size="sm"
            type="button"
          >
            <tab.icon className="w-5 h-5" />
            <span>{tab.label}</span>
            <span
              className={`fi-count-badge ${activeTab === tab.id ? 'bg-white/20' : 'bg-slate-700/50'}`}
            >
              {tab.count}
            </span>
          </Button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-gradient-to-br from-slate-900/50 to-slate-800/50 border border-slate-700 rounded-xl p-6 backdrop-blur-sm min-h-[400px]">
        {/* Seeds Tab */}
        {activeTab === 'seeds' && (
          <div className="fi-empty-state">
            <Sparkles className="w-16 h-16 fi-text-purple mx-auto mb-4" />
            <h3 className="fi-title-xl mb-2">Contenido FI</h3>
            <p className="text-slate-400 mb-6">
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
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-bold text-white">Trivias de Salud</h3>
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
                <Plus className="w-4 h-4" />
                Nueva Trivia
              </Button>
            </div>

            {/* Trivias List */}
            {isLoading ? (
              <div className="fi-empty-state">
                <div className="inline-block w-8 h-8 border-4 border-slate-600 border-t-emerald-500 rounded-full animate-spin"></div>
                <p className="mt-4 text-slate-400">Cargando trivias...</p>
              </div>
            ) : trivias.length === 0 ? (
              <div className="fi-empty-state">
                <p className="text-slate-400">No hay trivias configuradas</p>
                <p className="text-sm text-slate-500 mt-2">
                  Haz click en &quot;Nueva Trivia&quot; para crear una
                </p>
              </div>
            ) : (
              <div className="fi-stack-md">
                {trivias.map((trivia, index) => (
                  <div
                    key={trivia.id}
                    className="bg-gradient-to-br from-slate-800/50 to-slate-700/50 border border-slate-600 rounded-xl p-4 hover:border-emerald-600/50 transition-all"
                  >
                    <div className="flex items-start gap-4">
                      {/* Number Badge */}
                      <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-600/30 to-teal-600/30 border border-emerald-500/50 flex items-center justify-center">
                        <span className="text-lg font-bold text-emerald-200">{index + 1}</span>
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between mb-2">
                          <h4 className="text-base font-semibold text-white truncate pr-4">
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
                            <span className="px-2 py-0.5 rounded-full fi-text-xs-medium bg-slate-700/50 fi-text whitespace-nowrap">
                              {trivia.category}
                            </span>
                          </div>
                        </div>

                        {/* Options Preview */}
                        <div className="grid grid-cols-2 gap-2 mb-2">
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
                          <div className="flex flex-wrap gap-1">
                            {trivia.tags.map((tag) => (
                              <span
                                key={tag}
                                className="px-2 py-0.5 bg-slate-700/30 text-slate-400 text-xs rounded"
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
                          className="p-2 rounded-lg bg-blue-900/20 hover:bg-blue-900/30 fi-text-primary transition-colors"
                          title="Editar"
                          variant="ghost"
                          size="sm"
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          type="button"
                          className="p-2 rounded-lg bg-red-900/20 hover:bg-red-900/30 fi-text-error transition-colors opacity-50 cursor-not-allowed"
                          title="Eliminar (próximamente)"
                          disabled
                          variant="ghost"
                          size="sm"
                        >
                          <Trash2 className="w-4 h-4" />
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
            <Activity className="w-16 h-16 fi-text-purple mx-auto mb-4" />
            <h3 className="fi-title-xl mb-2">Ejercicios de Respiración</h3>
            <p className="text-slate-400 mb-6">3 ejercicios configurados (Box, 4-7-8, Coherent)</p>
            <p className="fi-text-muted">Editor de ejercicios disponible próximamente</p>
          </div>
        )}

        {/* Tips Tab */}
        {activeTab === 'tips' && (
          <div className="fi-empty-state">
            <Lightbulb className="w-16 h-16 fi-text-purple mx-auto mb-4" />
            <h3 className="fi-title-xl mb-2">Tips de Salud</h3>
            <p className="text-slate-400 mb-6">
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
