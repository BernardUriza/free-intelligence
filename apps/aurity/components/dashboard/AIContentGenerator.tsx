/**
 * AIContentGenerator - Generate AI-powered health content for TV display
 *
 * Card: FI-UI-FEAT-TVD-002
 * Uses waitingRoomAPI to generate health tips and trivia questions
 * that can be added to the TV display rotation.
 */

'use client';

import { useState, useCallback } from 'react';
import { Sparkles, Lightbulb, HelpCircle, RefreshCw, Send, Check, Copy, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { waitingRoomAPI, type TipCategory } from '@/lib/api/waiting-room';
import { AI_CONTENT_CATEGORIES, AI_TRIVIA_DIFFICULTIES } from '@/lib/dashboard/constants';
import { getDynamicIcon } from '@/lib/icons';

interface AIContentGeneratorProps {
  /** Callback when content is ready to be added to TV */
  onContentGenerated?: (content: GeneratedContent) => void;
  /** Clinic ID for context */
  clinicId?: string;
}

export interface GeneratedContent {
  type: 'tip' | 'trivia';
  content: string;
  metadata?: {
    category?: string;
    difficulty?: string;
    options?: string[];
    correctAnswer?: number;
    explanation?: string;
  };
}

export function AIContentGenerator({
  onContentGenerated,
}: AIContentGeneratorProps) {
  const [activeGenerator, setActiveGenerator] = useState<'tip' | 'trivia'>('tip');
  const [selectedCategory, setSelectedCategory] = useState<TipCategory>('nutrition');
  const [selectedDifficulty, setSelectedDifficulty] = useState<'easy' | 'medium' | 'hard'>('easy');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedContent, setGeneratedContent] = useState<GeneratedContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerateTip = useCallback(async () => {
    setIsGenerating(true);
    setError(null);
    setGeneratedContent(null);

    try {
      const response = await waitingRoomAPI.generateTip({ category: selectedCategory });

      const content: GeneratedContent = {
        type: 'tip',
        content: response.tip,
        metadata: {
          category: selectedCategory,
        },
      };

      setGeneratedContent(content);
    } catch (err) {
      console.error('Failed to generate tip:', err);
      setError('Error al generar el tip. Intenta de nuevo.');
    } finally {
      setIsGenerating(false);
    }
  }, [selectedCategory]);

  const handleGenerateTrivia = useCallback(async () => {
    setIsGenerating(true);
    setError(null);
    setGeneratedContent(null);

    try {
      const response = await waitingRoomAPI.generateTrivia({ difficulty: selectedDifficulty });

      const content: GeneratedContent = {
        type: 'trivia',
        content: response.question,
        metadata: {
          difficulty: selectedDifficulty,
          options: response.options,
          correctAnswer: response.correct_answer,
          explanation: response.explanation,
        },
      };

      setGeneratedContent(content);
    } catch (err) {
      console.error('Failed to generate trivia:', err);
      setError('Error al generar la trivia. Intenta de nuevo.');
    } finally {
      setIsGenerating(false);
    }
  }, [selectedDifficulty]);

  const handleAddToTV = useCallback(() => {
    if (generatedContent && onContentGenerated) {
      onContentGenerated(generatedContent);
      setGeneratedContent(null);
    }
  }, [generatedContent, onContentGenerated]);

  const handleCopy = useCallback(() => {
    if (generatedContent) {
      const textToCopy = generatedContent.type === 'tip'
        ? generatedContent.content
        : `${generatedContent.content}\n\nOpciones:\n${generatedContent.metadata?.options?.map((o, i) => `${i + 1}. ${o}`).join('\n')}\n\nRespuesta correcta: ${(generatedContent.metadata?.correctAnswer || 0) + 1}\n\n${generatedContent.metadata?.explanation}`;

      navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [generatedContent]);

  return (
    <div className="fi-stack-xl">
      {/* Generator Type Selector */}
      <div className="flex gap-2">
        <Button
          onClick={() => {
            setActiveGenerator('tip');
            setGeneratedContent(null);
          }}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border transition-all ${
            activeGenerator === 'tip'
              ? 'bg-purple-600/20 border-purple-500/50 text-purple-300'
              : 'bg-slate-900/50 border-slate-700 text-slate-400 hover:text-white hover:border-slate-600'
          }`}
          variant={activeGenerator === 'tip' ? 'primary' : 'ghost'}
          size="sm"
          type="button"
        >
          <Lightbulb className="w-5 h-5" />
          <span className="font-medium">Tips de Salud</span>
        </Button>
        <Button
          onClick={() => {
            setActiveGenerator('trivia');
            setGeneratedContent(null);
          }}
          className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border transition-all ${
            activeGenerator === 'trivia'
              ? 'bg-purple-600/20 border-purple-500/50 text-purple-300'
              : 'bg-slate-900/50 border-slate-700 text-slate-400 hover:text-white hover:border-slate-600'
          }`}
          variant={activeGenerator === 'trivia' ? 'primary' : 'ghost'}
          size="sm"
          type="button"
        >
          <HelpCircle className="w-5 h-5" />
          <span className="font-medium">Trivia Educativa</span>
        </Button>
      </div>

      {/* Configuration Panel */}
      {activeGenerator === 'tip' ? (
        <div className="space-y-3">
          <label className="block text-sm font-medium fi-text">
            Categoría del tip
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {AI_CONTENT_CATEGORIES.map((cat) => {
              const CategoryIcon = getDynamicIcon(cat.iconKey);
              return (
                <Button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id as TipCategory)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-left transition-all ${
                    selectedCategory === cat.id
                      ? 'bg-purple-600/20 border-purple-500/50 text-purple-300'
                      : 'bg-slate-900/50 border-slate-700 text-slate-400 hover:text-white hover:border-slate-600'
                  }`}
                  variant={selectedCategory === cat.id ? 'primary' : 'ghost'}
                  size="sm"
                  type="button"
                >
                  <span aria-hidden="true">
                    <CategoryIcon className="w-5 h-5" strokeWidth={1.5} />
                  </span>
                  <span className="text-sm font-medium">{cat.label}</span>
                </Button>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <label className="block text-sm font-medium fi-text">
            Dificultad de la trivia
          </label>
          <div className="grid grid-cols-3 gap-2">
            {AI_TRIVIA_DIFFICULTIES.map((diff) => (
              <Button
                key={diff.id}
                onClick={() => setSelectedDifficulty(diff.id as 'easy' | 'medium' | 'hard')}
                className={`px-4 py-3 rounded-lg border text-center transition-all ${
                  selectedDifficulty === diff.id
                    ? 'bg-purple-600/20 border-purple-500/50 text-purple-300'
                    : 'bg-slate-900/50 border-slate-700 text-slate-400 hover:text-white hover:border-slate-600'
                }`}
                variant={selectedDifficulty === diff.id ? 'primary' : 'ghost'}
                size="sm"
                type="button"
              >
                <span className="block text-sm font-medium">{diff.label}</span>
                <span className="block fi-text-xs-muted mt-1">{diff.description}</span>
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Generate Button */}
      <Button
        onClick={activeGenerator === 'tip' ? handleGenerateTip : handleGenerateTrivia}
        disabled={isGenerating}
        variant="purple"
        size="lg"
        className="w-full"
        icon={isGenerating ? RefreshCw : Sparkles}
        loading={isGenerating}
      >
        {isGenerating
          ? 'Generando con IA...'
          : `Generar ${activeGenerator === 'tip' ? 'Tip' : 'Trivia'}`}
      </Button>

      {/* Error Display */}
      {error && (
        <div className="p-4 bg-red-950/20 border border-red-700/30 rounded-lg">
          <p className="text-sm fi-text-error">{error}</p>
        </div>
      )}

      {/* Generated Content Preview */}
      {generatedContent && (
        <div className="p-4 bg-slate-900/50 border border-slate-700 rounded-lg space-y-4">
          <div className="fi-flex-between">
            <div className="fi-flex-gap">
              <Sparkles className="w-4 h-4 fi-text-purple" />
              <span className="text-sm font-medium text-purple-300">
                {generatedContent.type === 'tip' ? 'Tip Generado' : 'Trivia Generada'}
              </span>
            </div>
            <div className="fi-flex-gap">
              <Button
                onClick={handleCopy}
                variant="ghost"
                size="sm"
                icon={copied ? Check : Copy}
                className={copied ? 'fi-text-success' : ''}
                title="Copiar contenido"
                aria-label="Copiar contenido"
              />
            </div>
          </div>

          {generatedContent.type === 'tip' ? (
            <div className="p-4 bg-gradient-to-br from-purple-950/40 to-slate-950/40 border border-purple-600/30 rounded-lg">
              <p className="text-white leading-relaxed">{generatedContent.content}</p>
              <p className="text-xs fi-text-purple mt-3">
                Categoría: {AI_CONTENT_CATEGORIES.find(c => c.id === generatedContent.metadata?.category)?.label}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="p-4 bg-gradient-to-br from-purple-950/40 to-slate-950/40 border border-purple-600/30 rounded-lg">
                <p className="text-white font-medium mb-4">{generatedContent.content}</p>
                <div className="fi-stack-sm">
                  {generatedContent.metadata?.options?.map((option, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border ${
                        idx === generatedContent.metadata?.correctAnswer
                          ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300'
                          : 'bg-slate-800/50 border-slate-700 fi-text'
                      }`}
                    >
                      <span className="font-mono text-sm mr-2">{idx + 1}.</span>
                      {option}
                      {idx === generatedContent.metadata?.correctAnswer && (
                        <Check className="w-4 h-4 inline ml-2" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
              {generatedContent.metadata?.explanation && (
                <div className="p-3 bg-blue-950/20 border border-blue-700/30 rounded-lg">
                  <p className="text-xs fi-text-primary font-medium mb-1">Explicación:</p>
                  <p className="text-sm text-blue-300">{generatedContent.metadata.explanation}</p>
                </div>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <Button
              onClick={activeGenerator === 'tip' ? handleGenerateTip : handleGenerateTrivia}
              disabled={isGenerating}
              variant="secondary"
              size="sm"
              icon={RefreshCw}
              className="flex-1"
            >
              Regenerar
            </Button>
            <Button
              onClick={handleAddToTV}
              variant="success"
              size="sm"
              icon={Send}
              className="flex-1"
            >
              Añadir a TV
            </Button>
          </div>
        </div>
      )}

      {/* Info Footer */}
      <div className="flex items-start gap-3 p-3 bg-slate-900/30 border border-slate-700/50 rounded-lg">
        <Info className="fi-icon-md fi-icon-slate flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="fi-text-xs leading-relaxed">
            El contenido es generado por Free Intelligence AI y se almacena en caché por 30 minutos para optimizar costos.
            Todo el contenido generado es revisado para asegurar precisión médica general.
          </p>
        </div>
      </div>
    </div>
  );
}
