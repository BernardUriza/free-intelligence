/**
 * LLMModelCard Component
 *
 * Displays an LLM model in grid view with config and actions.
 */

'use client';

import { Edit, Trash2, Power, PowerOff, FlaskConical } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { LLMModel } from '@aurity-standalone/types/llm';
import { PROVIDER_INFO, COST_TIER_INFO } from '@aurity-standalone/types/llm';
import { ProviderLogo, ProviderLogoBox } from '@/components/ui/ProviderLogo';

interface LLMModelCardProps {
  model: LLMModel;
  isSelected: boolean;
  onClick: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onToggleActive: () => void;
  onTest?: () => void;
}

export function LLMModelCard({
  model,
  isSelected,
  onClick,
  onEdit,
  onDelete,
  onToggleActive,
  onTest,
}: LLMModelCardProps) {
  const providerInfo = PROVIDER_INFO[model.provider] || { label: model.provider, icon: '?', color: 'slate' };
  const costInfo = COST_TIER_INFO[model.cost_tier] || { label: model.cost_tier, icon: '?', color: 'slate' };

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

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(0)}K`;
    }
    return num.toString();
  };

  const formatBytes = (bytes: number) => {
    if (bytes >= 1024 * 1024 * 1024) {
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
    }
    if (bytes >= 1024 * 1024) {
      return `${(bytes / (1024 * 1024)).toFixed(0)} MB`;
    }
    return `${(bytes / 1024).toFixed(0)} KB`;
  };

  const isLocalModel = model.provider === 'ollama';

  return (
    <div
      className={`p-6 rounded-xl border-2 cursor-pointer transition-all ${
        isSelected
          ? 'border-emerald-500 bg-emerald-950/30 shadow-lg shadow-emerald-900/20'
          : model.is_active
          ? 'border-slate-700 bg-slate-900/50 hover:border-slate-600 hover:bg-slate-900/70'
          : 'border-slate-800 bg-slate-950/50 opacity-60'
      }`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="fi-flex-gap-md">
          <ProviderLogoBox provider={model.provider} size={28} />
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              {model.id}
              {!model.is_active && (
                <span className="px-2 py-0.5 text-xs bg-red-900/50 fi-text-error rounded-full">
                  Inactivo
                </span>
              )}
            </h3>
            <p className="fi-text-xs">{providerInfo.label}</p>
          </div>
        </div>
        <div className="fi-flex-gap-sm">
          <Button
            onClick={(e) => {
              e.stopPropagation();
              onToggleActive();
            }}
            variant="ghost"
            size="sm"
            icon={model.is_active ? PowerOff : Power}
            aria-label={model.is_active ? 'Desactivar modelo' : 'Activar modelo'}
            title={model.is_active ? 'Desactivar' : 'Activar'}
            className={model.is_active ? 'text-yellow-400 hover:bg-yellow-900/30' : 'fi-text-green hover:bg-green-900/30'}
          />
          {model.is_active && onTest && (
            <Button
              onClick={(e) => {
                e.stopPropagation();
                onTest();
              }}
              variant="ghost"
              size="sm"
              icon={FlaskConical}
              aria-label="Probar modelo"
              title="Probar modelo"
              className="fi-text-purple hover:text-purple-300 hover:bg-purple-900/30"
            />
          )}
          <Button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            variant="ghost"
            size="sm"
            icon={Edit}
            aria-label="Editar modelo"
          />
          <Button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            variant="ghost"
            size="sm"
            icon={Trash2}
            aria-label="Eliminar modelo"
            className="text-slate-400 hover:fi-text-error hover:bg-red-900/30"
          />
        </div>
      </div>

      {/* Label */}
      <p className="text-sm fi-text mb-4 line-clamp-1 min-h-[1.25rem]">
        {model.label}
      </p>

      {/* Description */}
      {model.description && (
        <p className="fi-text-xs mb-4 line-clamp-2 min-h-[2rem]">
          {model.description}
        </p>
      )}

      {/* Config Summary */}
      <div className="grid grid-cols-2 gap-2 mb-4">
        <div className="fi-card-mini">
          <div className="fi-text-xs-muted">Proveedor</div>
          <div className="fi-title-sm-medium flex items-center gap-1.5">
            <ProviderLogo provider={model.provider} size={14} />
            {providerInfo.label}
          </div>
        </div>
        {/* Show RAM size for local models, Cost tier for cloud models */}
        {isLocalModel ? (
          <div className="fi-card-mini">
            <div className="fi-text-xs-muted">RAM</div>
            <div className="text-sm font-mono fi-text-info">
              {model.size_bytes ? formatBytes(model.size_bytes) : '—'}
            </div>
          </div>
        ) : (
          <div className="fi-card-mini">
            <div className="fi-text-xs-muted">Costo</div>
            <div className={`text-sm font-medium text-${costInfo.color}-400`}>
              {costInfo.icon} {costInfo.label}
            </div>
          </div>
        )}
        <div className="fi-card-mini">
          <div className="fi-text-xs-muted">Max Tokens</div>
          <div className="text-sm font-mono text-white">{formatNumber(model.max_tokens)}</div>
        </div>
        <div className="fi-card-mini">
          <div className="fi-text-xs-muted">Contexto</div>
          <div className="text-sm font-mono text-white">{formatNumber(model.context_window)}</div>
        </div>
      </div>

      {/* Last Updated */}
      <div className="pt-3 fi-border-top fi-text-xs-muted">
        Actualizado: {formatDate(model.updated_at)}
      </div>
    </div>
  );
}
