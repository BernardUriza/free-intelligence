/**
 * useClinicDetails Hook
 *
 * Single Responsibility: Loads doctors, appointments, and doctor limits
 * for the currently selected clinic.
 * Extracted from useClinicsAdmin for SRP compliance.
 *
 * Card: FI-CHECKIN-002
 */

'use client';

import { useState, useCallback } from 'react';
import type { Clinic, Doctor, Appointment, DoctorLimitInfo } from '@/lib/api/clinics';
import type { DoctorSaveData } from '@/components/admin/clinics/DoctorDetailModal';
import {
  fetchDoctors,
  updateDoctor,
  fetchAppointments,
  fetchDoctorLimits,
} from '@/lib/api/clinics';
import { toastError } from '@/lib/swal';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('ClinicDetails');

export function useClinicDetails() {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [doctorLimits, setDoctorLimits] = useState<DoctorLimitInfo | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  const loadClinicDetails = useCallback(async (clinic: Clinic) => {
    setLoadingDetails(true);
    try {
      const [doctorsData, appointmentsData, limitsData] = await Promise.all([
        fetchDoctors(clinic.clinic_id, true),
        fetchAppointments(clinic.clinic_id),
        fetchDoctorLimits(clinic.clinic_id),
      ]);
      setDoctors(doctorsData);
      setAppointments(appointmentsData);
      setDoctorLimits(limitsData);
    } catch (err) {
      log.error('Failed to load clinic details', { error: String(err) });
    } finally {
      setLoadingDetails(false);
    }
  }, []);

  const handleUpdateDoctor = useCallback(async (
    clinicId: string,
    doctor: Doctor,
    data: DoctorSaveData,
  ) => {
    try {
      const updated = await updateDoctor(clinicId, doctor.doctor_id, data);
      setDoctors((prev) =>
        prev.map((d) => (d.doctor_id === updated.doctor_id ? updated : d)),
      );
    } catch (err) {
      log.error('Failed to update doctor', { error: String(err) });
      toastError(err instanceof Error ? err.message : 'Error al actualizar doctor');
      throw err;
    }
  }, []);

  const handleDoctorCreated = useCallback((
    newDoctor: Doctor,
    clinicId: string | undefined,
  ) => {
    setDoctors((prev) => [...prev, newDoctor]);
    if (clinicId) {
      fetchDoctorLimits(clinicId).then(setDoctorLimits);
    }
  }, []);

  const reloadDoctorLimits = useCallback((clinicId: string | undefined) => {
    if (clinicId) {
      fetchDoctorLimits(clinicId).then(setDoctorLimits);
    }
  }, []);

  return {
    doctors,
    appointments,
    doctorLimits,
    loadingDetails,
    loadClinicDetails,
    handleUpdateDoctor,
    handleDoctorCreated,
    reloadDoctorLimits,
  } as const;
}
