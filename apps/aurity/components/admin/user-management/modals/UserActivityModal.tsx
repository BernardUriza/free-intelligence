'use client';

import { Button } from '@/components/ui/button';
import type { User } from '../types';

interface UserActivityModalProps {
  user: User;
  onClose: () => void;
}

export function UserActivityModal({ user, onClose }: UserActivityModalProps) {
  // TODO: Replace with real data from HDF5:/audit_logs
  const activities = [
    { timestamp: new Date(), action: 'Login exitoso', ip: '192.168.1.100' },
    { timestamp: new Date(Date.now() - 3600000), action: 'Sesión creada', details: 'session_20251120_001' },
    { timestamp: new Date(Date.now() - 7200000), action: 'Exportación de datos', details: 'corpus_export.json' },
    { timestamp: new Date(Date.now() - 86400000), action: 'Login exitoso', ip: '192.168.1.100' },
  ];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]" onClick={onClose}>
      <div className="bg-slate-800 rounded-lg max-w-2xl w-full max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="p-6 fi-border-bottom">
          <h3 className="fi-title">Historial de Actividad</h3>
          <p className="fi-subtitle mt-1">{user.email}</p>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="fi-stack-md">
            {activities.map((activity, idx) => (
              <div key={idx} className="flex gap-3 pb-3 border-b border-slate-800 last:border-0">
                <div className="flex-shrink-0 w-16 fi-text-xs-muted text-right pt-1">
                  {activity.timestamp.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}
                </div>
                <div className="flex-1">
                  <p className="text-sm text-white font-medium">{activity.action}</p>
                  {activity.details && (
                    <p className="fi-text-xs font-mono mt-1">{activity.details}</p>
                  )}
                  {activity.ip && (
                    <p className="fi-text-xs-muted mt-1">IP: {activity.ip}</p>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 bg-yellow-900/20 border border-yellow-700/30 rounded-lg p-4">
            <p className="text-xs text-yellow-400/80">
              🚧 Logs completos de actividad se integrarán con el sistema de auditoría (HDF5:/audit_logs)
            </p>
          </div>
        </div>

        <div className="p-4 fi-border-top flex justify-end">
          <Button onClick={onClose} variant="secondary">
            Cerrar
          </Button>
        </div>
      </div>
    </div>
  );
}
