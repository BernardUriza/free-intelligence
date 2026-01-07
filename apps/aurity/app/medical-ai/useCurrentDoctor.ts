/**
 * useCurrentDoctor Hook
 *
 * Fetches the current user's doctor profile based on their clinic membership.
 * Used in medical-ai to allow doctors to view/edit their availability.
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import {
  getClinicMembership,
  fetchDoctor,
  updateDoctor,
  type Doctor,
  type DoctorUpdate,
  type ClinicMembership,
} from '@/lib/api/clinics';

interface UseCurrentDoctorResult {
  doctor: Doctor | null;
  membership: ClinicMembership | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  updateDoctorProfile: (data: DoctorUpdate) => Promise<void>;
}

export function useCurrentDoctor(): UseCurrentDoctorResult {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [membership, setMembership] = useState<ClinicMembership | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCurrentDoctor = useCallback(async () => {
    if (!user?.sub) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 1. Get clinic membership
      const membershipData = await getClinicMembership(user.sub, user.email);

      if (!membershipData) {
        setMembership(null);
        setDoctor(null);
        setLoading(false);
        return;
      }

      setMembership(membershipData);

      // 2. Fetch full doctor profile
      const doctorData = await fetchDoctor(
        membershipData.clinic_id,
        membershipData.doctor_id
      );

      setDoctor(doctorData);
    } catch (err) {
      console.error('[useCurrentDoctor] Error:', err);
      setError(err instanceof Error ? err.message : 'Error al cargar perfil');
    } finally {
      setLoading(false);
    }
  }, [user?.sub, user?.email]);

  // Fetch on mount and when auth changes
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchCurrentDoctor();
    } else if (!authLoading && !isAuthenticated) {
      setLoading(false);
    }
  }, [authLoading, isAuthenticated, fetchCurrentDoctor]);

  // Update doctor profile
  const updateDoctorProfile = useCallback(async (data: DoctorUpdate) => {
    if (!membership || !doctor) {
      throw new Error('No doctor profile to update');
    }

    const updated = await updateDoctor(
      membership.clinic_id,
      doctor.doctor_id,
      data
    );

    setDoctor(updated);
  }, [membership, doctor]);

  return {
    doctor,
    membership,
    loading: authLoading || loading,
    error,
    refetch: fetchCurrentDoctor,
    updateDoctorProfile,
  };
}
