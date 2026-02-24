/**
 * useDerivedDisplayValues Hook
 *
 * Single Responsibility: computed display strings derived from
 * domain entities (doctor, clinic, appointment).
 * Pure derivation — no side-effects.
 */

import { useMemo } from 'react';
import type { Appointment } from '@/components/bryntum/utils/appointment-transform.utils';
import type { Doctor, Clinic } from '@/lib/api/clinics';

interface UseDerivedDisplayValuesArgs {
  effectiveDoctor: Doctor | null;
  activeAppointment: Appointment | null;
  isSuperAdmin: boolean;
  selectedClinicId: string | null;
  clinics: Clinic[];
  membershipClinicName: string | undefined;
}

export function useDerivedDisplayValues({
  effectiveDoctor,
  activeAppointment,
  isSuperAdmin,
  selectedClinicId,
  clinics,
  membershipClinicName,
}: UseDerivedDisplayValuesArgs) {
  const appointmentTimeDisplay = useMemo(() => {
    if (!activeAppointment?.scheduled_at) return null;
    const date = new Date(activeAppointment.scheduled_at);
    return date.toLocaleTimeString('es-MX', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  }, [activeAppointment?.scheduled_at]);

  const clinicName = useMemo(() => {
    if (isSuperAdmin && selectedClinicId) {
      return clinics.find((c) => c.clinic_id === selectedClinicId)?.name || 'Clínica';
    }
    return membershipClinicName || 'Clínica';
  }, [isSuperAdmin, selectedClinicId, clinics, membershipClinicName]);

  const doctorDisplayName = useMemo(() => {
    return (
      effectiveDoctor?.display_name ||
      (effectiveDoctor ? `${effectiveDoctor.nombre} ${effectiveDoctor.apellido}` : 'Doctor')
    );
  }, [effectiveDoctor]);

  return { appointmentTimeDisplay, clinicName, doctorDisplayName };
}
