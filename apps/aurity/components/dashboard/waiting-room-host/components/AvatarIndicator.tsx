'use client';

/**
 * AvatarIndicator - Avatar icon with "EN VIVO" indicator
 */

import { memo } from 'react';
import { Hand } from 'lucide-react';

export const AvatarIndicator = memo(function AvatarIndicator() {
  return (
    <div className="flex-shrink-0">
      <div className="w-16 h-16 sm:w-20 sm:h-20 lg:w-24 lg:h-24 rounded-full bg-gradient-to-br from-purple-600/20 to-purple-800/20 border-2 border-purple-500/40 flex items-center justify-center shadow-lg shadow-purple-500/20">
        <Hand className="w-8 h-8 sm:w-10 sm:h-10 lg:w-12 lg:h-12 text-purple-300" strokeWidth={1.5} aria-hidden="true" />
      </div>
      {/* Live indicator */}
      <div className="flex items-center justify-center gap-2 mt-2 sm:mt-3">
        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse shadow-lg shadow-green-500/50" />
        <span className="text-[10px] sm:fi-text-xs-medium fi-text-green tracking-wide">
          EN VIVO
        </span>
      </div>
    </div>
  );
});
