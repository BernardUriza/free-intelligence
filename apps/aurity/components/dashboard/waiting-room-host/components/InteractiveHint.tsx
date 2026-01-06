'use client';

/**
 * InteractiveHint - QR code hint for interactive mode
 */

import { memo } from 'react';

export const InteractiveHint = memo(function InteractiveHint() {
  return (
    <div className="mt-3 sm:mt-4 text-center flex-shrink-0">
      <div className="inline-flex items-center gap-2 px-3 sm:px-4 py-2 bg-purple-900/30 border border-purple-500/30 rounded-lg">
        <span className="text-xs sm:text-sm text-purple-300">
          Escanea el código QR para interactuar →
        </span>
        {/* Placeholder for QR code */}
        <div className="w-12 h-12 sm:w-16 sm:h-16 bg-white rounded flex items-center justify-center">
          <span className="text-xs text-slate-900">QR</span>
        </div>
      </div>
    </div>
  );
});
