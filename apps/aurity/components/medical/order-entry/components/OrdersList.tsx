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
      <div className="fi-gradient-slate-card-muted backdrop-blur-sm rounded-2xl p-12 border border-dashed border-slate-700/50 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-slate-800/50 rounded-2xl mb-4">
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
            className="fi-gradient-slate-card backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50 shadow-xl"
          >
            <div className="flex items-center gap-3 mb-5">
              <div className={`p-2 ${typeConfig.gradientClass} rounded-lg`}>
                <span className="text-2xl">{typeConfig.icon}</span>
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
                  className="group flex items-start justify-between p-4 bg-slate-900/80 rounded-xl border border-slate-700/50 hover:border-slate-600/50 transition-all"
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
                          <span className="inline-flex items-center gap-1 mt-2 px-2 py-1 bg-cyan-500/10 fi-text-info text-xs rounded-md">
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
                    className="opacity-0 group-hover:opacity-100 fi-text-error hover:text-red-300 hover:bg-red-500/10 ml-4"
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
