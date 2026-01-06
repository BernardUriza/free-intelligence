'use client';

/**
 * ClinicFooter - Branding footer with clinic name
 */

import { memo } from 'react';

interface ClinicFooterProps {
  /** Clinic name */
  clinicName: string;
}

export const ClinicFooter = memo(function ClinicFooter({
  clinicName,
}: ClinicFooterProps) {
  return (
    <div className="mt-auto pt-3 sm:pt-4 fi-border-top/50 flex-shrink-0">
      <div className="flex items-center justify-between text-xs sm:fi-subtitle">
        <div className="fi-flex-gap">
          <span className="font-medium fi-text">{clinicName}</span>
          <span>·</span>
          <span>Powered by AURITY</span>
        </div>
        <div className="fi-flex-gap">
          <div className="w-2 h-2 bg-emerald-500 rounded-full" />
          <span>Sistema On-Premise</span>
        </div>
      </div>
    </div>
  );
});
