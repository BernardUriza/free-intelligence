/**
 * useClinicsAdmin Hook (Compositor)
 *
 * Thin orchestrator that composes focused sub-hooks into a unified API
 * for the Clinics Admin page.
 *
 * Sub-hooks (SRP):
 * - useClinics: Clinic list CRUD
 * - useClinicDetails: Doctors, appointments, limits for selected clinic
 * - useClinicMembership: Membership state and link-to-clinic flow
 *
 * Card: FI-CHECKIN-002
 */

'use client';

import { useEffect, useCallback } from 'react';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useRBAC } from '@aurity-standalone/hooks/useRBAC';
import type { Doctor } from '@/lib/api/clinics';
import type { DoctorSaveData } from '@/components/admin/clinics/DoctorDetailModal';
import { useClinics } from '@/hooks/useClinics';
import { useClinicDetails } from '@/hooks/useClinicDetails';
import { useClinicMembership } from '@/hooks/useClinicMembership';
import type { Clinic } from '@/lib/api/clinics';

export function useClinicsAdmin() {
  const { user } = useAuth();
  const { isSuperAdmin } = useRBAC();

  const {
    clinics,
    loading,
    error,
    selectedClinic,
    setSelectedClinic,
    loadClinics,
    handleCreateClinic,
    handleDeleteClinic,
  } = useClinics();

  const {
    doctors,
    appointments,
    doctorLimits,
    loadingDetails,
    loadClinicDetails: loadDetails,
    handleUpdateDoctor: updateDoctor,
    handleDoctorCreated: doctorCreated,
    reloadDoctorLimits: reloadLimits,
  } = useClinicDetails();

  const {
    membership,
    linkingToClinic,
    loadMembership,
    handleLinkToClinic: linkToClinic,
  } = useClinicMembership();

  // ── Effects ───────────────────────────────────────────────────────

  useEffect(() => {
    loadClinics();
  }, [loadClinics]);

  useEffect(() => {
    if (user?.sub) {
      loadMembership({ sub: user.sub, email: user.email });
    }
  }, [user?.sub, user?.email, loadMembership]);

  // ── Bridged callbacks (connect sub-hooks) ─────────────────────────

  const loadClinicDetails = useCallback(async (clinic: Clinic) => {
    setSelectedClinic(clinic);
    await loadDetails(clinic);
  }, [setSelectedClinic, loadDetails]);

  const handleUpdateDoctor = useCallback(async (doctor: Doctor, data: DoctorSaveData) => {
    if (!selectedClinic) return;
    await updateDoctor(selectedClinic.clinic_id, doctor, data);
  }, [selectedClinic, updateDoctor]);

  const handleDoctorCreated = useCallback((newDoctor: Doctor) => {
    doctorCreated(newDoctor, selectedClinic?.clinic_id);
  }, [selectedClinic?.clinic_id, doctorCreated]);

  const reloadDoctorLimits = useCallback(() => {
    reloadLimits(selectedClinic?.clinic_id);
  }, [selectedClinic?.clinic_id, reloadLimits]);

  const handleLinkToClinic = useCallback(async (form: { nombre: string; apellido: string; especialidad: string; role: string }) => {
    if (!user?.sub || !selectedClinic) return;
    return linkToClinic(
      { sub: user.sub, email: user.email },
      selectedClinic,
      form as Parameters<typeof linkToClinic>[2],
      () => loadClinicDetails(selectedClinic),
    );
  }, [user?.sub, user?.email, selectedClinic, linkToClinic, loadClinicDetails]);

  return {
    user,
    isSuperAdmin,
    clinics,
    loading,
    error,
    selectedClinic,
    loadClinics,
    loadClinicDetails,
    handleCreateClinic,
    handleDeleteClinic,
    doctors,
    doctorLimits,
    handleUpdateDoctor,
    handleDoctorCreated,
    reloadDoctorLimits,
    appointments,
    loadingDetails,
    membership,
    linkingToClinic,
    handleLinkToClinic,
  };
}

