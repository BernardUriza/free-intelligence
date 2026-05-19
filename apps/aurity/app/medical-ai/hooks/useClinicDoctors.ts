/**
 * useClinicDoctors Hook
 *
 * Fetches all doctors from a clinic for admin users.
 * Used in medical-ai to allow admins to switch between doctors' calendars.
 */

import { useState, useEffect, useCallback } from 'react';
import { createLogger } from '@/lib/internal/logger';
import { fetchDoctors, type Doctor } from '@/lib/api/clinics';

const log = createLogger('ClinicDoctors');

interface UseClinicDoctorsResult {
  doctors: Doctor[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useClinicDoctors(clinicId: string | undefined): UseClinicDoctorsResult {
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchClinicDoctors = useCallback(async () => {
    if (!clinicId) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await fetchDoctors(clinicId);
      setDoctors(data);
    } catch (err) {
      log.error('Failed to load doctors', { error: String(err) });
      setError(err instanceof Error ? err.message : 'Error al cargar doctores');
    } finally {
      setLoading(false);
    }
  }, [clinicId]);

  useEffect(() => {
    fetchClinicDoctors();
  }, [fetchClinicDoctors]);

  return {
    doctors,
    loading,
    error,
    refetch: fetchClinicDoctors,
  };
}
