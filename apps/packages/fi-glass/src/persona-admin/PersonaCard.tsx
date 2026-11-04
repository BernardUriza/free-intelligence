'use client';

import type { CSSProperties, KeyboardEvent } from 'react';
import { Brain, Edit, Trash2 } from 'lucide-react';
import { AdminButton } from '../admin-kit';
import { FI_PERSONA_ROOT_CLASS, usePersonaAdminStyle } from './personaAdminStyle';
import type { Persona, PersonaHideableField } from './types';

export interface PersonaCardProps {
  persona: Persona;
  selected?: boolean;
  onSelect?: () => void;
  onEdit: () => void;
  /** Omit for a persona that must not be deleted. */
  onDelete?: () => void;
  /** Any CSS color; tints the card border and icon. */
  accentColor?: string;
  hiddenFields?: readonly PersonaHideableField[];
  locale?: string;
}

function formatDate(iso: string, locale: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' });
}

export function PersonaCard({
  persona,
  selected = false,
  onSelect,
  onEdit,
  onDelete,
  accentColor,
  hiddenFields = [],
  locale = 'es-MX',
}: PersonaCardProps) {
  usePersonaAdminStyle();
  const hidden = new Set(hiddenFields);
  const stats = persona.usage_stats;
  const style = accentColor ? ({ '--fi-persona-accent': accentColor, '--fi-admin-accent': accentColor } as CSSProperties) : undefined;
  const onKey = (e: KeyboardEvent<HTMLElement>) => {
    if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      onSelect?.();
    }
  };

  return (
    <article
      className={`${FI_PERSONA_ROOT_CLASS} fi-persona-card`}
      data-selected={selected}
      style={style}
      tabIndex={0}
      aria-label={persona.name}
      onClick={onSelect}
      onKeyDown={onKey}
    >
      <div className="fi-persona-card-head">
        <div className="fi-persona-card-id">
          <span className="fi-persona-card-icon">
            <Brain size={22} aria-hidden="true" />
          </span>
          <div style={{ minWidth: 0 }}>
            <h3 className="fi-persona-card-name">{persona.name}</h3>
            {persona.version !== undefined ? <p className="fi-persona-subtitle">v{persona.version}</p> : null}
          </div>
        </div>
        <div className="fi-persona-actions">
          <AdminButton
            variant="ghost"
            iconOnly
            icon={Edit}
            aria-label="Editar persona"
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
          />
          {onDelete ? (
            <AdminButton
              variant="ghost"
              iconOnly
              icon={Trash2}
              aria-label="Eliminar persona"
              title="Eliminar persona"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
            />
          ) : null}
        </div>
      </div>

      <p className="fi-persona-card-desc">{persona.description}</p>

      <dl className="fi-persona-card-stats" style={{ margin: 0 }}>
        <div className="fi-persona-mini">
          <dt>Modelo</dt>
          <dd title={persona.model}>{persona.model}</dd>
        </div>
        {hidden.has('voice') ? null : (
          <div className="fi-persona-mini">
            <dt>Voz</dt>
            <dd>{persona.voice || 'N/A'}</dd>
          </div>
        )}
        {hidden.has('temperature') ? null : (
          <div className="fi-persona-mini">
            <dt>Temperature</dt>
            <dd>{persona.temperature.toFixed(2)}</dd>
          </div>
        )}
        {hidden.has('max_tokens') ? null : (
          <div className="fi-persona-mini">
            <dt>Max tokens</dt>
            <dd>{persona.max_tokens.toLocaleString(locale)}</dd>
          </div>
        )}
      </dl>

      {stats || persona.last_updated ? (
        <div className="fi-persona-card-foot">
          {stats ? (
            <>
              <div className="fi-persona-row">
                <span>Invocaciones</span>
                <b>{stats.total_invocations.toLocaleString(locale)}</b>
              </div>
              <div className="fi-persona-row">
                <span>Latencia promedio</span>
                <b>{stats.avg_latency_ms > 0 ? `${stats.avg_latency_ms.toFixed(0)}ms` : 'N/A'}</b>
              </div>
              <div className="fi-persona-row">
                <span>Costo promedio</span>
                <b>{stats.avg_cost_usd > 0 ? `$${stats.avg_cost_usd.toFixed(4)}` : 'N/A'}</b>
              </div>
            </>
          ) : null}
          {persona.last_updated ? (
            <span>
              Actualizado: {formatDate(persona.last_updated, locale)}
              {persona.updated_by ? ` por ${persona.updated_by}` : ''}
            </span>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
