'use client';

/**
 * DoctorLimitBadge
 *
 * Displays the current doctor count vs limit for a clinic.
 * Shows color-coded status: green (ok), yellow (near limit), red (at limit).
 *
 * File: apps/aurity/components/admin/clinics/DoctorLimitBadge.tsx
 * Created: 2025-12-31
 */

import { useEffect, useState } from 'react';
import { Users, Infinity } from 'lucide-react';
import type { DoctorLimitInfo } from '@/lib/api/clinics';
import { fetchDoctorLimits } from '@/lib/api/clinics';

interface DoctorLimitBadgeProps {
  clinicId: string;
  /** Optional: Use pre-fetched data instead of fetching */
  limits?: DoctorLimitInfo | null;
  /** Show compact version (just numbers) */
  compact?: boolean;
}

export function DoctorLimitBadge({
  clinicId,
  limits: propLimits,
  compact = false,
}: DoctorLimitBadgeProps) {
  const [limits, setLimits] = useState<DoctorLimitInfo | null>(propLimits ?? null);
  const [loading, setLoading] = useState(!propLimits);

  useEffect(() => {
    if (propLimits) {
      setLimits(propLimits);
      setLoading(false);
      return;
    }

    fetchDoctorLimits(clinicId)
      .then(setLimits)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [clinicId, propLimits]);

  if (loading) {
    return (
      <div className="px-2 py-1 bg-slate-700/50 rounded text-xs text-slate-500 animate-pulse">
        ...
      </div>
    );
  }

  if (!limits) {
    return null;
  }

  const { current_count, max_allowed, has_override } = limits;
  const isUnlimited = max_allowed === null;
  const percentage = isUnlimited ? 0 : (current_count / max_allowed) * 100;
  const isAtLimit = !isUnlimited && current_count >= max_allowed;
  const isNearLimit = !isUnlimited && percentage >= 80;

  // Color classes based on status
  const colorClasses = isAtLimit
    ? 'bg-red-500/20 text-red-400 border-red-500/30'
    : isNearLimit
      ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
      : 'bg-slate-700/50 text-slate-400 border-slate-600/30';

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${colorClasses}`}
        title={
          isUnlimited
            ? 'Sin límite de doctores'
            : `${current_count} de ${max_allowed} doctores${has_override ? ' (override)' : ''}`
        }
      >
        {current_count}/{isUnlimited ? <Infinity className="w-3 h-3" /> : max_allowed}
        {has_override && <span className="text-yellow-400">*</span>}
      </span>
    );
  }

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs border ${colorClasses}`}
    >
      <Users className="w-3.5 h-3.5" />
      <span className="font-medium">
        {current_count}
        <span className="text-slate-500 mx-1">/</span>
        {isUnlimited ? (
          <span className="inline-flex items-center gap-0.5">
            <Infinity className="w-3 h-3" />
          </span>
        ) : (
          max_allowed
        )}
      </span>
      <span className="text-slate-500">doctores</span>
      {has_override && (
        <span
          className="text-yellow-400 font-medium"
          title="Límite personalizado por superadmin"
        >
          (override)
        </span>
      )}
    </div>
  );
}
