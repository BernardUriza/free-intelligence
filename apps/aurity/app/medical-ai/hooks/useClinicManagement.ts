/**
 * useClinicManagement Hook
 *
 * Single Responsibility: clinic/doctor selection state for admin users.
 * - Fetches clinics for superadmins
 * - Provides effective clinic/doctor IDs
 * - Handles doctor & clinic switching
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { createLogger } from '@/lib/internal/logger';
import { fetchClinics, type Doctor, type Clinic } from '@/lib/api/clinics';
import { useClinicDoctors } from './useClinicDoctors';

const log = createLogger('ClinicManagement');

interface UseClinicManagementArgs {
  isSuperAdmin: boolean;
  isClinicAdmin: boolean;
  membershipClinicId: string | undefined;
  currentDoctor: Doctor | null;
}

export function useClinicManagement({
  isSuperAdmin,
  isClinicAdmin,
  membershipClinicId,
  currentDoctor,
}: UseClinicManagementArgs) {
  // ── Clinics (superadmin only) ──────────────────────────────────────────
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [selectedClinicId, setSelectedClinicId] = useState<string | null>(null);
  const [loadingClinics, setLoadingClinics] = useState(false);

  useEffect(() => {
    if (!isSuperAdmin) {
      setClinics([]);
      return;
    }

    let cancelled = false;
    setLoadingClinics(true);

    fetchClinics()
      .then((data) => {
        if (cancelled) return;
        setClinics(data);
        setSelectedClinicId((prev) =>
          prev || membershipClinicId || data[0]?.clinic_id || null,
        );
      })
      .catch((err) => {
        if (!cancelled) {
          log.error('Failed to fetch clinics', { error: String(err) });
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingClinics(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isSuperAdmin, membershipClinicId]);

  // ── Effective IDs ──────────────────────────────────────────────────────
  const effectiveClinicId = isSuperAdmin ? selectedClinicId : membershipClinicId ?? null;

  // ── Doctors (admin) ────────────────────────────────────────────────────
  const { doctors: clinicDoctors, loading: loadingDoctors } = useClinicDoctors(
    isClinicAdmin ? (effectiveClinicId ?? undefined) : undefined,
  );

  const [selectedDoctorId, setSelectedDoctorId] = useState<string | null>(null);

  // Default to current doctor
  useEffect(() => {
    if (currentDoctor && !selectedDoctorId) {
      setSelectedDoctorId(currentDoctor.doctor_id);
    }
  }, [currentDoctor, selectedDoctorId]);

  const effectiveDoctor = useMemo(() => {
    if (isClinicAdmin && selectedDoctorId) {
      return clinicDoctors.find((d) => d.doctor_id === selectedDoctorId) || null;
    }
    return currentDoctor;
  }, [isClinicAdmin, selectedDoctorId, clinicDoctors, currentDoctor]);

  // ── Selection handlers ─────────────────────────────────────────────────
  const handleSelectDoctor = useCallback((selected: Doctor) => {
    setSelectedDoctorId(selected.doctor_id);
  }, []);

  const handleSelectClinic = useCallback((selected: Clinic) => {
    setSelectedClinicId(selected.clinic_id);
    setSelectedDoctorId(null); // reset doctor on clinic change
  }, []);

  return {
    clinics,
    selectedClinicId,
    loadingClinics,
    clinicDoctors,
    loadingDoctors,
    effectiveClinicId,
    effectiveDoctor,
    handleSelectDoctor,
    handleSelectClinic,
  };
}
