/**
 * ModelsFilterBar
 *
 * Single Responsibility: Provider filter dropdown and include-inactive toggle
 * for the LLM Models Admin page.
 *
 * Route: /admin/models
 */

'use client';

import { Filter } from 'lucide-react';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import type { LLMProvider } from '@aurity-standalone/types/llm';
import { PROVIDER_INFO } from '@aurity-standalone/types/llm';

interface ModelsFilterBarProps {
  providerFilter: LLMProvider | '';
  onProviderChange: (value: LLMProvider | '') => void;
  includeInactive: boolean;
  onIncludeInactiveChange: (value: boolean) => void;
}

export function ModelsFilterBar({
  providerFilter,
  onProviderChange,
  includeInactive,
  onIncludeInactiveChange,
}: ModelsFilterBarProps) {
  return (
    <div className="mdl-filters-row">
      <div className="fi-flex-gap">
        <Filter className="mdl-icon-sm" />
        <Select
          value={providerFilter}
          onValueChange={(val) => onProviderChange(val as LLMProvider | '')}
        >
          <SelectTrigger className="mdl-filter-select">
            <SelectValue placeholder="Todos los proveedores" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Todos los proveedores</SelectItem>
            {Object.entries(PROVIDER_INFO).map(([key, info]) => (
              <SelectItem key={key} value={key}>
                {info.icon} {info.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <label className="mdl-checkbox-label">
        <input
          type="checkbox"
          checked={includeInactive}
          onChange={(e) => onIncludeInactiveChange(e.target.checked)}
          className="mdl-checkbox"
        />
        Mostrar inactivos
      </label>
    </div>
  );
}
