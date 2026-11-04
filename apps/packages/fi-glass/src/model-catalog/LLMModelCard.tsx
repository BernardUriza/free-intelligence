'use client';

import type { KeyboardEvent, MouseEvent } from 'react';
import { Edit, FlaskConical, Power, PowerOff, Trash2 } from 'lucide-react';
import { AdminButton } from '../admin-kit';
import { COST_TIER_INFO, PROVIDER_INFO, formatBytes, formatCount, formatDate, isLocalProvider } from './format';
import { FI_MODEL_CATALOG_ROOT_CLASS, useModelCatalogStyle } from './modelCatalogStyle';
import { ProviderLogo, ProviderLogoBox } from './ProviderLogo';
import type { LLMModel } from './types';

export interface LLMModelCardProps {
  model: LLMModel;
  selected?: boolean;
  onSelect?: () => void;
  onEdit: () => void;
  onDeactivate: () => void;
  onToggleActive: () => void;
  /** Omit to hide the test action. It is offered only on active models. */
  onTest?: () => void;
  locale?: string;
}

export function LLMModelCard({
  model,
  selected = false,
  onSelect,
  onEdit,
  onDeactivate,
  onToggleActive,
  onTest,
  locale = 'es-MX',
}: LLMModelCardProps) {
  useModelCatalogStyle();
  const providerLabel = PROVIDER_INFO[model.provider]?.label ?? model.provider;
  const cost = COST_TIER_INFO[model.cost_tier];
  const onKey = (e: KeyboardEvent<HTMLElement>) => {
    if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      onSelect?.();
    }
  };
  const act = (fn: () => void) => (e: MouseEvent) => {
    e.stopPropagation();
    fn();
  };

  return (
    <article
      className={`${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-card`}
      data-selected={selected}
      data-active={model.is_active}
      tabIndex={0}
      aria-label={model.id}
      onClick={onSelect}
      onKeyDown={onKey}
    >
      <div className="fi-mc-card-head">
        <div className="fi-mc-card-id">
          <ProviderLogoBox provider={model.provider} />
          <div style={{ minWidth: 0 }}>
            <h3 className="fi-mc-card-name">
              {model.id}
              {model.is_active ? null : <span className="fi-mc-badge">Inactivo</span>}
            </h3>
            <p className="fi-mc-small" style={{ margin: 0 }}>
              {providerLabel}
            </p>
          </div>
        </div>
        <div className="fi-mc-actions">
          <AdminButton
            variant="ghost"
            iconOnly
            tone={model.is_active ? 'on' : 'off'}
            icon={model.is_active ? PowerOff : Power}
            aria-label={model.is_active ? 'Desactivar modelo' : 'Activar modelo'}
            title={model.is_active ? 'Desactivar' : 'Activar'}
            onClick={act(onToggleActive)}
          />
          {model.is_active && onTest ? (
            <AdminButton
              variant="ghost"
              iconOnly
              tone="secondary"
              icon={FlaskConical}
              aria-label="Probar modelo"
              title="Probar modelo"
              onClick={act(onTest)}
            />
          ) : null}
          <AdminButton variant="ghost" iconOnly icon={Edit} aria-label="Editar modelo" onClick={act(onEdit)} />
          <AdminButton
            variant="ghost"
            iconOnly
            tone="danger"
            icon={Trash2}
            aria-label="Eliminar modelo"
            onClick={act(onDeactivate)}
          />
        </div>
      </div>

      <p className="fi-mc-clamp1">{model.label}</p>
      {model.description ? <p className="fi-mc-clamp2">{model.description}</p> : null}

      <dl className="fi-mc-stats">
        <div className="fi-mc-mini">
          <dt>Proveedor</dt>
          <dd>
            <ProviderLogo provider={model.provider} size={14} />
            {providerLabel}
          </dd>
        </div>
        {isLocalProvider(model.provider) ? (
          <div className="fi-mc-mini">
            <dt>RAM</dt>
            <dd>{model.size_bytes ? formatBytes(model.size_bytes) : '—'}</dd>
          </div>
        ) : (
          <div className="fi-mc-mini">
            <dt>Costo</dt>
            <dd>{cost ? `${cost.symbol} ${cost.label}` : model.cost_tier}</dd>
          </div>
        )}
        <div className="fi-mc-mini">
          <dt>Max Tokens</dt>
          <dd>{formatCount(model.max_tokens)}</dd>
        </div>
        <div className="fi-mc-mini">
          <dt>Contexto</dt>
          <dd>{formatCount(model.context_window)}</dd>
        </div>
      </dl>

      <div className="fi-mc-card-foot">Actualizado: {formatDate(model.updated_at, locale)}</div>
    </article>
  );
}
