/**
 * PersonaCard Component
 *
 * Displays a persona in grid view with stats, edit, and delete buttons.
 */

'use client';

import { Brain, Edit, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { Persona } from '@aurity-standalone/types/persona';
import { PERSONA_COLORS } from '@aurity-standalone/types/persona';

// Protected personas that cannot be deleted
const PROTECTED_PERSONAS = new Set(['general_assistant', 'soap_editor']);

// Static class map — avoids dynamic Tailwind interpolation (breaks purge)
const PERSONA_CARD_CLASSES: Record<string, { default: string; selected: string; icon: string; brain: string }> = {
  emerald: { default: 'admin-persona-emerald', selected: 'admin-persona-emerald-selected', icon: 'admin-persona-icon-emerald', brain: 'admin-persona-brain-emerald' },
  blue:    { default: 'admin-persona-blue',    selected: 'admin-persona-blue-selected',    icon: 'admin-persona-icon-blue',    brain: 'admin-persona-brain-blue' },
  purple:  { default: 'admin-persona-purple',  selected: 'admin-persona-purple-selected',  icon: 'admin-persona-icon-purple',  brain: 'admin-persona-brain-purple' },
  rose:    { default: 'admin-persona-rose',    selected: 'admin-persona-rose-selected',    icon: 'admin-persona-icon-rose',    brain: 'admin-persona-brain-rose' },
  slate:   { default: 'admin-persona-slate',   selected: 'admin-persona-slate-selected',   icon: 'admin-persona-icon-slate',   brain: 'admin-persona-brain-slate' },
};

interface PersonaCardProps {
  persona: Persona;
  isSelected: boolean;
  onClick: () => void;
  onEdit: () => void;
  /** Handler for delete action (only shown for non-protected personas) */
  onDelete?: () => void;
}

export function PersonaCard({ persona, isSelected, onClick, onEdit, onDelete }: PersonaCardProps) {
  const color = PERSONA_COLORS[persona.id as keyof typeof PERSONA_COLORS] || 'slate';
  const classes = PERSONA_CARD_CLASSES[color] || PERSONA_CARD_CLASSES.slate;
  const isProtected = PROTECTED_PERSONAS.has(persona.id);

  // Format last updated date
  const formatDate = (isoDate: string) => {
    try {
      const date = new Date(isoDate);
      return date.toLocaleDateString('es-MX', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return 'Fecha inválida';
    }
  };

  return (
    <div
      className={isSelected ? classes.selected : classes.default}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="fi-flex-gap-md">
          <div className={classes.icon}>
            <Brain className={classes.brain} />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">{persona.name}</h3>
            <p className="fi-text-xs">v{persona.version}</p>
          </div>
        </div>
        <div className="fi-flex-gap-sm">
          <Button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            variant="ghost"
            size="sm"
            icon={Edit}
            aria-label="Editar persona"
          />
          {/* Delete button - only shown for non-protected personas */}
          {!isProtected && onDelete && (
            <Button
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              variant="ghost"
              size="sm"
              icon={Trash2}
              aria-label="Eliminar persona"
              title="Eliminar persona"
              className="admin-persona-delete-btn"
            />
          )}
        </div>
      </div>

      {/* Description */}
      <p className="text-sm fi-text mb-4 line-clamp-2 min-h-[2.5rem]">
        {persona.description}
      </p>

      {/* Config Summary */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="fi-card-mini">
          <div className="fi-text-xs-muted">Model</div>
          <div className="text-sm font-mono text-white truncate" title={persona.model}>
            {persona.model}
          </div>
        </div>
        <div className="fi-card-mini">
          <div className="fi-text-xs-muted">Voice</div>
          <div className="text-sm font-mono text-white capitalize" title={persona.voice || 'No configurada'}>
            {persona.voice || 'N/A'}
          </div>
        </div>
        <div className="fi-card-mini">
          <div className="fi-text-xs-muted">Temperature</div>
          <div className="text-sm font-mono text-white">{persona.temperature.toFixed(2)}</div>
        </div>
        <div className="fi-card-mini">
          <div className="fi-text-xs-muted">Max Tokens</div>
          <div className="text-sm font-mono text-white">{persona.max_tokens.toLocaleString()}</div>
        </div>
      </div>

      {/* Usage Stats */}
      <div className="pt-4 fi-border-top">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">Invocaciones</span>
          <span className="font-semibold text-white">
            {persona.usage_stats.total_invocations.toLocaleString()}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs mt-1">
          <span className="text-slate-500">Latencia Promedio</span>
          <span className="font-semibold text-white">
            {persona.usage_stats.avg_latency_ms > 0
              ? `${persona.usage_stats.avg_latency_ms.toFixed(0)}ms`
              : 'N/A'}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs mt-1">
          <span className="text-slate-500">Costo Promedio</span>
          <span className="font-semibold text-white">
            {persona.usage_stats.avg_cost_usd > 0
              ? `$${persona.usage_stats.avg_cost_usd.toFixed(4)}`
              : 'N/A'}
          </span>
        </div>
      </div>

      {/* Last Updated */}
      <div className="mt-3 pt-3 fi-border-top fi-text-xs-muted">
        Actualizado: {formatDate(persona.last_updated)} por {persona.updated_by}
      </div>
    </div>
  );
}
