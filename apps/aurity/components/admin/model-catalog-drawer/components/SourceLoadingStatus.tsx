'use client';

import { Loader2, AlertCircle } from 'lucide-react';
import { SOURCE_INFO, type CatalogSource } from '@/lib/api/catalog';
import { ProviderLogo } from '@/components/ui/ProviderLogo';
import type { SourceState } from '../types';
import { SOURCES } from '../constants';

interface SourceLoadingStatusProps {
  sourceStates: Record<CatalogSource, SourceState>;
}

export function SourceLoadingStatus({ sourceStates }: SourceLoadingStatusProps) {
  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {SOURCES.map((source) => {
        const state = sourceStates[source];
        const info = SOURCE_INFO[source];
        const modelCount = state.models.length;

        let statusColor = 'bg-slate-800 text-slate-400 border-slate-700';
        let statusIndicator = null;
        let statusText = '';

        if (state.status === 'loading') {
          statusColor = 'bg-blue-900/30 fi-text-primary border-blue-700/50';
          statusIndicator = <Loader2 className="w-3.5 h-3.5 animate-spin" />;
          statusText = 'Cargando...';
        } else if (state.status === 'loaded') {
          statusColor = 'bg-emerald-900/30 fi-text-success border-emerald-700/50';
          statusIndicator = <span className="w-2 h-2 rounded-full bg-emerald-400" />;
          statusText = `${modelCount}`;
        } else if (state.status === 'error') {
          statusColor = 'bg-red-900/30 fi-text-error border-red-700/50';
          statusIndicator = <AlertCircle className="w-3.5 h-3.5" />;
          statusText = 'Error';
        }

        return (
          <div
            key={source}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full fi-text-xs-medium border transition-all ${statusColor}`}
          >
            {statusIndicator}
            <ProviderLogo provider={source} size={14} />
            <span>{info.label}</span>
            {statusText && (
              <span className="px-1.5 py-0.5 text-[10px] bg-black/30 rounded-full">
                {statusText}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
