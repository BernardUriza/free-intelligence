'use client';

// =============================================================================
// Offline Status Indicator - SOLID Refactor
// =============================================================================
// Single Responsibility: Only handles offline/online UI feedback
// =============================================================================

import { usePWAOnline } from '@/lib/pwa/context';
import { WifiOff, RefreshCw } from 'lucide-react';

export function OfflineIndicator() {
  const { isOnline, wasOffline, enabled } = usePWAOnline();

  if (!enabled) return null;

  // Syncing state (just came back online)
  if (wasOffline && isOnline) {
    return (
      <div className="fixed left-0 right-0 top-0 z-50">
        <div className="bg-green-600 text-white px-4 py-2 text-center text-sm font-medium flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span>Conexion restaurada. Sincronizando...</span>
        </div>
      </div>
    );
  }

  // Offline state
  if (!isOnline) {
    return (
      <div className="fixed left-0 right-0 top-0 z-50">
        <div className="bg-amber-600 text-white px-4 py-2 text-center text-sm font-medium flex items-center justify-center gap-2">
          <WifiOff className="w-4 h-4" />
          <span>Sin conexion. Los cambios se guardaran localmente.</span>
        </div>
      </div>
    );
  }

  return null;
}
