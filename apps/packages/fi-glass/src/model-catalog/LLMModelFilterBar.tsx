'use client';

import { useId } from 'react';
import { Filter } from 'lucide-react';
import { PROVIDER_INFO } from './format';
import { FI_MODEL_CATALOG_ROOT_CLASS, useModelCatalogStyle } from './modelCatalogStyle';
import type { LLMProvider } from './types';

export interface LLMModelFilterBarProps {
  provider: LLMProvider | '';
  onProviderChange: (provider: LLMProvider | '') => void;
  includeInactive: boolean;
  onIncludeInactiveChange: (includeInactive: boolean) => void;
}

export function LLMModelFilterBar({
  provider,
  onProviderChange,
  includeInactive,
  onIncludeInactiveChange,
}: LLMModelFilterBarProps) {
  useModelCatalogStyle();
  const id = useId();
  return (
    <div className={`${FI_MODEL_CATALOG_ROOT_CLASS} fi-mc-filters`}>
      <label className="fi-mc-inline" htmlFor={id}>
        <Filter size={16} aria-hidden="true" className="fi-mc-muted" />
        <span className="fi-mc-label">Proveedor</span>
      </label>
      <select
        id={id}
        className="fi-mc-input"
        value={provider}
        onChange={(e) => onProviderChange(e.target.value as LLMProvider | '')}
      >
        <option value="">Todos los proveedores</option>
        {(Object.keys(PROVIDER_INFO) as LLMProvider[]).map((key) => (
          <option key={key} value={key}>
            {PROVIDER_INFO[key].label}
          </option>
        ))}
      </select>
      <label className="fi-mc-check" style={{ marginLeft: 'auto' }}>
        <input
          type="checkbox"
          checked={includeInactive}
          onChange={(e) => onIncludeInactiveChange(e.target.checked)}
        />
        Mostrar inactivos
      </label>
    </div>
  );
}
