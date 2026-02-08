/**
 * useClinicsAdmin Hook
 *
 * Encapsulates all state management and data fetching for the Clinics Admin page.
 * Single Responsibility: Data layer for clinics, doctors, appointments, and membership.
 *
 * Card: FI-CHECKIN-002
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useRBAC } from '@aurity-standalone/hooks/useRBAC';
import type { Clinic, ClinicCreate, Doctor, Appointment, ClinicMembership, ClinicRole, DoctorLimitInfo } from '@/lib/api/clinics';
import type { DoctorSaveData } from '@/components/admin/clinics/DoctorDetailModal';
import {
  fetchClinics,
  createClinic,
  deleteClinic,
  fetchDoctors,
  updateDoctor,
  fetchAppointments,
  getClinicMembership,
  linkToClinic,
  fetchDoctorLimits,
} from '@/lib/api/clinics';
import { confirmDialog, toastError } from '@/lib/swal';

interface LinkForm {
  nombre: string;
  apellido: string;
  especialidad: string;
  role: ClinicRole;
}

export function useClinicsAdmin() {
  const { user } = useAuth();
  const { isSuperAdmin } = useRBAC();

  // Core state
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedClinic, setSelectedClinic] = useState<Clinic | null>(null);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Membership
  const [membership, setMembership] = useState<ClinicMembership | null>(null);
  const [linkingToClinic, setLinkingToClinic] = useState(false);

  // Doctor limits
  const [doctorLimits, setDoctorLimits] = useState<DoctorLimitInfo | null>(null);

  // ── Data Loading ──────────────────────────────────────────────────

  const loadClinics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchClinics(false);
      setClinics(data);
    } catch (err) {
      console.error('Failed to load clinics:', err);
      setError(err instanceof Error ? err.message : 'Error al cargar las clínicas');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMembership = useCallback(async () => {
    if (!user?.sub) return;
    try {
      const data = await getClinicMembership(user.sub, user.email ?? undefined);
      setMembership(data);
    } catch (err) {
      console.error('Failed to load membership:', err);
    }
  }, [user?.sub, user?.email]);

  const loadClinicDetails = useCallback(async (clinic: Clinic) => {
    setSelectedClinic(clinic);
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
      console.error('Failed to load clinic details:', err);
    } finally {
      setLoadingDetails(false);
    }
  }, []);

  // ── Effects ───────────────────────────────────────────────────────

  useEffect(() => {
    loadClinics();
  }, [loadClinics]);

  useEffect(() => {
    if (user?.sub) {
      loadMembership();
    }
  }, [user?.sub, loadMembership]);

  // ── Mutations ─────────────────────────────────────────────────────

  const handleCreateClinic = useCallback(async (data: ClinicCreate) => {
    try {
      const newClinic = await createClinic(data);
      setClinics((prev) => [...prev, newClinic]);
    } catch (err) {
      console.error('Failed to create clinic:', err);
      throw err;
    }
  }, []);

  const handleDeleteClinic = useCallback(async (clinicId: string) => {
    const confirmed = await confirmDialog({
      title: '¿Desactivar clínica?',
      text: 'La clínica será desactivada pero no se eliminará permanentemente.',
      confirmText: 'Desactivar',
      icon: 'warning',
    });
    if (!confirmed) return;
    try {
      await deleteClinic(clinicId);
      setClinics((prev) =>
        prev.map((c) => (c.clinic_id === clinicId ? { ...c, is_active: false } : c))
      );
      if (selectedClinic?.clinic_id === clinicId) {
        setSelectedClinic(null);
      }
    } catch (err) {
      console.error('Failed to delete clinic:', err);
    }
  }, [selectedClinic?.clinic_id]);

  const handleUpdateDoctor = useCallback(async (doctor: Doctor, data: DoctorSaveData) => {
    if (!selectedClinic) return;
    try {
      const updated = await updateDoctor(
        selectedClinic.clinic_id,
        doctor.doctor_id,
        data
      );
      setDoctors((prev) =>
        prev.map((d) => (d.doctor_id === updated.doctor_id ? updated : d))
      );
    } catch (err) {
      console.error('Failed to update doctor:', err);
      toastError(err instanceof Error ? err.message : 'Error al actualizar doctor');
      throw err;
    }
  }, [selectedClinic]);

  const handleLinkToClinic = useCallback(async (form: LinkForm) => {
    if (!user?.sub || !selectedClinic) return;

    setLinkingToClinic(true);
    try {
      const result = await linkToClinic(
        user.sub,
        {
          clinic_id: selectedClinic.clinic_id,
          role: form.role,
          nombre: form.nombre,
          apellido: form.apellido,
          especialidad: form.especialidad || undefined,
        },
        user.email ?? undefined
      );

      if (result.success && result.membership) {
        setMembership(result.membership);
        loadClinicDetails(selectedClinic);
        return true;
      }
      return false;
    } catch (err) {
      console.error('Failed to link to clinic:', err);
      toastError(err instanceof Error ? err.message : 'Error al vincularse a la clínica');
      return false;
    } finally {
      setLinkingToClinic(false);
    }
  }, [user?.sub, user?.email, selectedClinic, loadClinicDetails]);

  const handleDoctorCreated = useCallback((newDoctor: Doctor) => {
    setDoctors((prev) => [...prev, newDoctor]);
    if (selectedClinic) {
      fetchDoctorLimits(selectedClinic.clinic_id).then(setDoctorLimits);
    }
  }, [selectedClinic]);

  const reloadDoctorLimits = useCallback(() => {
    if (selectedClinic) {
      fetchDoctorLimits(selectedClinic.clinic_id).then(setDoctorLimits);
    }
  }, [selectedClinic]);

  return {
    // Auth
    user,
    isSuperAdmin,

    // Clinics
    clinics,
    loading,
    error,
    selectedClinic,
    loadClinics,
    loadClinicDetails,
    handleCreateClinic,
    handleDeleteClinic,

    // Doctors
    doctors,
    doctorLimits,
    handleUpdateDoctor,
    handleDoctorCreated,
    reloadDoctorLimits,

    // Appointments
    appointments,
    loadingDetails,

    // Membership
    membership,
    linkingToClinic,
    handleLinkToClinic,
  };
}
