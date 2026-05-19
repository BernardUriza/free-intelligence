/**
 * useAppointmentForm Hook
 *
 * Manages form state, validation, and submission.
 */

import { useState, useCallback, useEffect } from 'react';
import { createLogger } from '@/lib/internal/logger';
import { getClinicTimeZone, TemporalAPI } from '@/lib/temporal';
import type { AppointmentDraft, AppointmentId } from '../types';

const log = createLogger('AppointmentForm');

interface UseAppointmentFormProps {
  mode: 'create' | 'edit';
  initialData?: Partial<AppointmentDraft & { appointment_id: AppointmentId }>;
  prefilledData?: { date?: Date; doctorId?: string; endDate?: Date } | null;
  defaultDoctorId: string;
  onSubmit: (payload: {
    appointment_id?: AppointmentId;
    patient_id: string;
    doctor_id: string;
    scheduled_at: string;
    appointment_type: AppointmentDraft['appointment_type'];
    estimated_duration: number;
    reason: string;
    notes?: string;
  }) => Promise<void>;
  onClose: () => void;
  onAfterSubmit?: () => void;
}

export function useAppointmentForm({
  mode,
  initialData,
  prefilledData,
  defaultDoctorId,
  onSubmit,
  onClose,
  onAfterSubmit,
}: UseAppointmentFormProps) {
  const initialDate = prefilledData?.date
    ? prefilledData.date.toISOString().split('T')[0]
    : new Date().toISOString().split('T')[0];
  const initialTime = prefilledData?.date
    ? `${String(prefilledData.date.getHours()).padStart(2, '0')}:${String(prefilledData.date.getMinutes()).padStart(2, '0')}`
    : '09:00';

  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [form, setForm] = useState<AppointmentDraft>({
    patient_id: '',
    doctor_id: prefilledData?.doctorId || defaultDoctorId,
    scheduled_date: initialDate,
    scheduled_time: initialTime,
    appointment_type: 'FIRST_TIME',
    estimated_duration: 30,
    reason: '',
    notes: '',
  });

  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setForm((prev) => ({
        ...prev,
        patient_id: initialData.patient_id ?? prev.patient_id,
        doctor_id: initialData.doctor_id ?? prev.doctor_id,
        scheduled_date: initialData.scheduled_date ?? prev.scheduled_date,
        scheduled_time: initialData.scheduled_time ?? prev.scheduled_time,
        appointment_type: (initialData.appointment_type as AppointmentDraft['appointment_type']) ?? prev.appointment_type,
        estimated_duration: initialData.estimated_duration ?? prev.estimated_duration,
        reason: initialData.reason ?? prev.reason,
        notes: initialData.notes ?? prev.notes,
      }));
    } else if (mode === 'create' && prefilledData) {
      const updates: Partial<AppointmentDraft> = {
        doctor_id: prefilledData.doctorId || defaultDoctorId,
      };

      if (prefilledData.date) {
        updates.scheduled_date = prefilledData.date.toISOString().split('T')[0];
        updates.scheduled_time = `${String(prefilledData.date.getHours()).padStart(2, '0')}:${String(prefilledData.date.getMinutes()).padStart(2, '0')}`;
      }

      if (prefilledData.date && prefilledData.endDate) {
        const durationMs = prefilledData.endDate.getTime() - prefilledData.date.getTime();
        const durationMinutes = Math.max(15, Math.round(durationMs / 60000));
        updates.estimated_duration = durationMinutes;
      }

      setForm((prev) => ({ ...prev, ...updates }));
    }
  }, [mode, initialData, prefilledData, defaultDoctorId]);

  const updateField = useCallback(<K extends keyof AppointmentDraft>(field: K, value: AppointmentDraft[K]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  }, []);

  const setPatientId = useCallback((patientId: string) => {
    setForm((prev) => ({ ...prev, patient_id: patientId }));
  }, []);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (!form.patient_id) {
        throw new Error('Selecciona o crea un paciente antes de continuar');
      }
      if (!form.doctor_id) {
        throw new Error('Selecciona un doctor');
      }
      if (!form.scheduled_date || !form.scheduled_time) {
        throw new Error('Fecha y hora son requeridas');
      }

      // Validate not in the past (allow current hour)
      const scheduledDateTime = new Date(`${form.scheduled_date}T${form.scheduled_time}:00`);
      const now = new Date();
      const currentHourStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours(), 0, 0);

      if (scheduledDateTime < currentHourStart) {
        throw new Error('No se pueden crear citas en el pasado');
      }

      // Convert clinic-local time to UTC instant via Temporal API
      const tz = getClinicTimeZone();
      const zdt = TemporalAPI.PlainDateTime.from(
        `${form.scheduled_date}T${form.scheduled_time}:00`
      ).toZonedDateTime(tz);
      const scheduled_at = zdt.toInstant().toString();
      const typeMap: Record<AppointmentDraft['appointment_type'], string> = {
        FIRST_TIME: 'first_visit',
        FOLLOW_UP: 'follow_up',
        PROCEDURE: 'procedure',
        EMERGENCY: 'emergency',
        TELEMEDICINE: 'telemedicine',
      };
      const backendType = typeMap[form.appointment_type] || 'follow_up';

      await onSubmit({
        appointment_id: initialData?.appointment_id,
        patient_id: form.patient_id,
        doctor_id: form.doctor_id,
        scheduled_at,
        appointment_type: backendType as any,
        estimated_duration: form.estimated_duration,
        reason: form.reason,
        notes: form.notes || undefined,
      });
      onAfterSubmit?.();
      onClose();
    } catch (err) {
      log.error('Submit failed', { error: String(err) });
      const msg = err instanceof Error ? err.message : 'No se pudo crear la cita';
      alert(msg);
    } finally {
      setLoading(false);
    }
  }, [form, onSubmit, onClose, onAfterSubmit, initialData?.appointment_id]);

  return {
    form,
    loading,
    deleting,
    setDeleting,
    updateField,
    setPatientId,
    handleSubmit,
  };
}
