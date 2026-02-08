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
      <div className="clinic-limit-loading">
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

  if (compact) {
    const badgeClass = isAtLimit
      ? 'clinic-limit-compact-critical'
      : isNearLimit
        ? 'clinic-limit-compact-warning'
        : 'clinic-limit-compact-ok';
    return (
      <span
        className={badgeClass}
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
      className={isAtLimit
        ? 'clinic-limit-full-critical'
        : isNearLimit
          ? 'clinic-limit-full-warning'
          : 'clinic-limit-full-ok'}
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
