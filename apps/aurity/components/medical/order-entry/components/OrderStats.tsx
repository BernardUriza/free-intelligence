'use client';

/**
 * OrderStats Component
 *
 * Quick stats grid showing order counts by type.
 */

import type { MedicalOrder } from '@aurity-standalone/api-client/medical-workflow';
import { ORDER_TYPES, ORDER_TYPE_KEYS } from '../constants';

interface OrderStatsProps {
  orders: MedicalOrder[];
}

export function OrderStats({ orders }: OrderStatsProps) {
  return (
    <div className="fi-grid-4">
      {ORDER_TYPE_KEYS.map(type => {
        const count = orders.filter(o => o.type === type).length;
        const typeConfig = ORDER_TYPES[type];

        return (
          <div
            key={type}
            className={`${typeConfig.gradientClass} backdrop-blur-sm rounded-xl p-4 border ${typeConfig.border} transition-all hover:scale-105`}
          >
            <div className="fi-flex-gap-md">
              <span className="text-3xl">{typeConfig.icon}</span>
              <div className="flex-1">
                <p className="fi-text-xs uppercase tracking-wide">{typeConfig.label}</p>
                <p className={`text-2xl font-bold ${typeConfig.text}`}>{count}</p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
