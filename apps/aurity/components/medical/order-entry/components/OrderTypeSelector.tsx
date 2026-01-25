'use client';

/**
 * OrderTypeSelector Component
 *
 * Grid of order type selection buttons with visual feedback.
 */

import type { OrderType } from '../types';
import { ORDER_TYPES, ORDER_TYPE_KEYS } from '../constants';
import { Button } from '@/components/ui/button';

interface OrderTypeSelectorProps {
  selectedType: OrderType;
  onSelect: (type: OrderType) => void;
}

export function OrderTypeSelector({ selectedType, onSelect }: OrderTypeSelectorProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {ORDER_TYPE_KEYS.map(type => {
        const isSelected = selectedType === type;
        const typeConfig = ORDER_TYPES[type];

        return (
          <Button
            key={type}
            onClick={() => onSelect(type)}
            className={`group relative p-4 rounded-xl border-2 transition-all duration-200 ${isSelected ? `${typeConfig.gradientClass} ${typeConfig.border} scale-105 shadow-lg` : 'bg-slate-900/50 border-slate-700/50 hover:border-slate-600 hover:scale-102'}`}
            variant={isSelected ? 'primary' : 'ghost'}
            size="sm"
            type="button"
          >
            <div className="mb-2 transform group-hover:scale-110 transition-transform">
              <typeConfig.icon className="w-8 h-8" strokeWidth={1.5} />
            </div>
            <div className={`text-sm font-medium ${isSelected ? typeConfig.text : 'fi-text'}`}>
              {typeConfig.label}
            </div>
            {isSelected && (
              <div className="fi-dot-pulse-emerald" />
            )}
          </Button>
        );
      })}
    </div>
  );
}
