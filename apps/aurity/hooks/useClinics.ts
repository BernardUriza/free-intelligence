/**
 * useClinics Hook
 *
 * Single Responsibility: Clinic list CRUD — load, create, delete, and select.
 * Extracted from useClinicsAdmin for SRP compliance.
 *
 * Card: FI-CHECKIN-002
 */

'use client';

import { useState, useCallback } from 'react';
import type { Clinic, ClinicCreate } from '@/lib/api/clinics';
import { fetchClinics, createClinic, deleteClinic } from '@/lib/api/clinics';
import { confirmDialog } from '@/lib/swal';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('Clinics');

export function useClinics() {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedClinic, setSelectedClinic] = useState<Clinic | null>(null);

  const loadClinics = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchClinics(false);
      setClinics(data);
    } catch (err) {
      log.error('Failed to load clinics', { error: String(err) });
      setError(err instanceof Error ? err.message : 'Error al cargar las clínicas');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleCreateClinic = useCallback(async (data: ClinicCreate) => {
    try {
      const newClinic = await createClinic(data);
      setClinics((prev) => [...prev, newClinic]);
    } catch (err) {
      log.error('Failed to create clinic', { error: String(err) });
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
        prev.map((c) => (c.clinic_id === clinicId ? { ...c, is_active: false } : c)),
      );
      if (selectedClinic?.clinic_id === clinicId) {
        setSelectedClinic(null);
      }
    } catch (err) {
      log.error('Failed to delete clinic', { error: String(err) });
    }
  }, [selectedClinic?.clinic_id]);

  return {
    clinics,
    loading,
    error,
    selectedClinic,
    setSelectedClinic,
    loadClinics,
    handleCreateClinic,
    handleDeleteClinic,
  } as const;
}
