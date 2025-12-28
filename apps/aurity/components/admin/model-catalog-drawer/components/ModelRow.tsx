'use client';

import { Check, ChevronRight, Cpu, Download, HardDrive, Loader2, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SOURCE_INFO, QUANT_INFO, formatBytes } from '@/lib/api/catalog';
import type { ModelRowProps } from '../types';

export function ModelRow({
  model,
  isInstalling,
  installProgress,
  onInstall,
  onDelete,
  featured = false,
  isSelected = false,
}: ModelRowProps) {
  const sourceInfo = SOURCE_INFO[model.source];
  const quantInfo = QUANT_INFO[model.quantization];

  return (
    <div
      data-model-item
      className={`group relative flex items-center gap-3 p-3 rounded-lg transition-all ${
        featured
          ? 'bg-amber-950/20 border border-amber-700/30 hover:border-amber-600/50'
          : model.is_installed
          ? 'bg-emerald-950/20 border border-emerald-700/30 hover:border-emerald-600/50'
          : 'bg-slate-800/50 border border-slate-700/50 hover:border-slate-600'
      } ${isSelected ? 'ring-2 ring-purple-500 ring-offset-2 ring-offset-slate-900' : ''}`}
    >
      {/* Source Icon */}
      <div className="flex-shrink-0 text-2xl" title={sourceInfo.label}>
        {sourceInfo.icon}
      </div>

      {/* Model Info */}
      <div className="flex-1 min-w-0">
        <div className="fi-flex-gap">
          <span className="font-medium text-white truncate">{model.name}</span>
          {model.is_installed && (
            <span className="flex-shrink-0 flex items-center gap-1 px-1.5 py-0.5 text-xs bg-emerald-700/50 text-emerald-300 rounded">
              <Check className="fi-icon-xs" />
            </span>
          )}
          {featured && !model.is_installed && (
            <span className="flex-shrink-0 px-1.5 py-0.5 text-xs bg-amber-700/50 text-amber-300 rounded">
              Popular
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5 fi-text-xs">
          <span className="fi-flex-gap-sm">
            <HardDrive className="fi-icon-xs" />
            {formatBytes(model.size_bytes)}
          </span>
          {model.ram_required_gb && (
            <span className="fi-flex-gap-sm">
              <Cpu className="fi-icon-xs" />
              {model.ram_required_gb.toFixed(1)} GB
            </span>
          )}
          <span>{quantInfo.label}</span>
          {model.parameters && <span>{model.parameters}</span>}
        </div>

        {/* Progress Bar */}
        {isInstalling && (
          <div className="mt-2">
            <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-purple-500 transition-all duration-300"
                style={{ width: `${installProgress}%` }}
              />
            </div>
            <span className="text-xs fi-text-purple mt-0.5">
              Instalando... {Math.round(installProgress)}%
            </span>
          </div>
        )}
      </div>

      {/* Action Button */}
      <div className="flex-shrink-0">
        {isInstalling ? (
          <div className="p-2">
            <Loader2 className="w-5 h-5 fi-text-purple animate-spin" />
          </div>
        ) : model.is_installed ? (
          <div className="fi-flex-gap-sm">
            <span className="text-xs fi-text-success mr-1">Listo</span>
            {model.source === 'ollama' && (
              <Button
                onClick={onDelete}
                variant="ghost"
                size="sm"
                icon={Trash2}
                className="text-slate-500 hover:fi-text-error hover:bg-red-950/30 opacity-0 group-hover:opacity-100"
                title="Eliminar"
                aria-label="Eliminar modelo"
              />
            )}
          </div>
        ) : (
          <Button
            onClick={onInstall}
            variant="primary"
            size="sm"
            icon={Download}
          >
            Instalar
          </Button>
        )}
      </div>

      {/* Expand indicator */}
      <ChevronRight className="w-4 h-4 text-slate-600 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  );
}
