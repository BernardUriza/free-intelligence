/**
 * AISidebar Component
 *
 * Right-side panel displaying AI suggestions and quick actions.
 * SRP: AI suggestions display only.
 *
 * @created 2026-02-22
 */

'use client';

import { Sparkles, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';

import type { AISuggestion } from '../types';
import { AISuggestionCard } from '../components';

interface AISidebarProps {
  suggestions: AISuggestion[];
}

export function AISidebar({ suggestions }: AISidebarProps) {
  return (
    <aside
      className="cnotes-ai-sidebar"
      aria-label="Panel de sugerencias de IA"
    >
      <div className="cnotes-ai-panel">
        <div className="cnotes-ai-header">
          <Sparkles
            className="cnotes-ai-icon fi-text-purple"
            aria-hidden="true"
          />
          <h3 className="cnotes-ai-title">Asistente IA</h3>
        </div>

        {suggestions.length === 0 ? (
          <p className="cnotes-ai-empty">
            Completa los campos para recibir sugerencias...
          </p>
        ) : (
          <div className="cnotes-ai-suggestions">
            {suggestions.map((suggestion, idx) => (
              <AISuggestionCard key={idx} suggestion={suggestion} />
            ))}
          </div>
        )}

        <div className="cnotes-ai-actions-wrap">
          <p className="cnotes-ai-actions-label">Acciones Rápidas</p>
          <div className="cnotes-diff-list">
            <Button
              variant="ghost"
              size="sm"
              icon={Sparkles}
              fullWidth
              className="cnotes-ai-quick-btn"
            >
              Generar resumen
            </Button>
            <Button
              variant="ghost"
              size="sm"
              icon={BookOpen}
              fullWidth
              className="cnotes-ai-quick-btn"
            >
              Buscar guías clínicas
            </Button>
          </div>
        </div>
      </div>
    </aside>
  );
}
