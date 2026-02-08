'use client';

/**
 * OrdersList Component
 *
 * Grouped display of medical orders by type.
 */

import { Trash2, ClipboardList } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { MedicalOrder } from '@aurity-standalone/api-client/medical-workflow';
import { ORDER_TYPES, ORDER_TYPE_KEYS } from '../constants';

interface OrdersListProps {
  groupedOrders: Record<string, MedicalOrder[]>;
  onRemove: (id: string) => void;
}

export function OrdersList({ groupedOrders, onRemove }: OrdersListProps) {
  const hasOrders = Object.keys(groupedOrders).length > 0;

  if (!hasOrders) {
    return (
      <div className="med-order-empty">
        <div className="med-order-empty-icon">
          <ClipboardList className="h-8 w-8 text-slate-600" />
        </div>
        <p className="text-slate-400 text-lg">No hay órdenes médicas aún</p>
        <p className="text-slate-500 text-sm mt-2">Agrega tu primera orden usando el formulario arriba</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {ORDER_TYPE_KEYS.map(type => {
        if (!groupedOrders[type]) return null;
        const typeConfig = ORDER_TYPES[type];

        return (
          <div
            key={type}
            className="med-order-group"
          >
            <div className="flex items-center gap-3 mb-5">
              <div className={`p-2 ${typeConfig.gradientClass} rounded-lg`}>
                <typeConfig.icon className="w-6 h-6" strokeWidth={1.5} />
              </div>
              <div className="flex-1">
                <h3 className="fi-title">{typeConfig.label}</h3>
                <p className="fi-subtitle">
                  {groupedOrders[type].length} {groupedOrders[type].length === 1 ? 'orden' : 'órdenes'}
                </p>
              </div>
            </div>

            <div className="fi-stack-md">
              {groupedOrders[type].map((order, index) => (
                <div
                  key={order.id}
                  className="group med-order-item"
                >
                  <div className="flex-1 space-y-1">
                    <div className="flex items-start gap-3">
                      <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full fi-text-xs-medium ${typeConfig.text} bg-slate-800/80`}>
                        {index + 1}
                      </span>
                      <div className="flex-1">
                        <p className="text-white font-medium leading-relaxed">{order.description}</p>
                        {order.details && (
                          <p className="fi-subtitle mt-2 leading-relaxed">{order.details}</p>
                        )}
                        {order.source === 'soap' && (
                          <span className="med-order-auto-badge">
                            <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full" />
                            Generada automáticamente
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <Button
                    onClick={() => onRemove(order.id)}
                    variant="ghost"
                    size="sm"
                    icon={Trash2}
                    className="med-order-remove-btn"
                    title="Eliminar orden"
                    aria-label="Eliminar orden"
                  />
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
