/**
 * useAppointmentActions Hook
 *
 * Single Responsibility: appointment lifecycle —
 * selecting, creating, starting workflows, and the
 * "start now?" confirmation flow.
 */

import { useState, useCallback, type Dispatch, type SetStateAction } from 'react';
import type { Appointment } from '@/components/bryntum/utils/appointment-transform.utils';
import { confirmDialog } from '@/lib/swal';
import type { PendingWorkflowData, AppointmentSubmitData } from '../types';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('AppointmentActions');

import type { Patient } from '@aurity-standalone/types/patient';
import type { Patient as MedicalPatient } from '@aurity-standalone/types/medical';

interface UseAppointmentActionsArgs {
  patients: Patient[];
  startAppointment: (id: string) => Promise<Appointment>;
  createAppointment: (data: {
    patient_id: string;
    scheduled_at: Date;
    appointment_type: string;
    estimated_duration: number;
    reason: string;
  }) => Promise<Appointment>;
  handleStartNewConsultation: (patient: Patient) => MedicalPatient;
  setIsExistingSession: (v: boolean) => void;
  setSessionDuration: (v: string) => void;
  resetWorkflow: () => void;
  setSelectedPatient: Dispatch<SetStateAction<MedicalPatient | null>>;
}

export function useAppointmentActions({
  patients,
  startAppointment,
  createAppointment,
  handleStartNewConsultation,
  setIsExistingSession,
  setSessionDuration,
  resetWorkflow,
  setSelectedPatient,
}: UseAppointmentActionsArgs) {
  const [activeAppointment, setActiveAppointment] = useState<Appointment | null>(null);
  const [showAppointmentModal, setShowAppointmentModal] = useState(false);
  const [selectedSlotTime, setSelectedSlotTime] = useState<Date | null>(null);
  const [pendingWorkflowData, setPendingWorkflowData] = useState<PendingWorkflowData | null>(null);

  // ── Start workflow from an existing appointment ────────────────────────
  const startWorkflowWithAppointment = useCallback(
    (patientId: string, appointment: Appointment) => {
      const patient = patients.find((p) => p.id === patientId);
      if (patient) {
        handleStartNewConsultation(patient);
        setActiveAppointment(appointment);
        setIsExistingSession(false);
        setSessionDuration('');
        resetWorkflow();
      }
    },
    [patients, handleStartNewConsultation, setIsExistingSession, setSessionDuration, resetWorkflow],
  );

  // ── Calendar: click on an appointment ──────────────────────────────────
  const handleSelectAppointment = useCallback(
    async (appointment: Appointment) => {
      const patient = patients.find((p) => p.id === appointment.patient_id);
      if (!patient) {
        log.error('Patient not found for appointment', { patientId: appointment.patient_id });
        return;
      }

      try {
        await startAppointment(appointment.appointment_id);
      } catch (error) {
        log.error('Failed to start appointment', { error: String(error) });
      }

      handleStartNewConsultation(patient);
      setActiveAppointment(appointment);
      setIsExistingSession(false);
      setSessionDuration('');
      resetWorkflow();
    },
    [patients, startAppointment, handleStartNewConsultation, setIsExistingSession, setSessionDuration, resetWorkflow],
  );

  // ── Calendar: click on an empty slot ───────────────────────────────────
  const handleCreateAppointment = useCallback((date: Date) => {
    setSelectedSlotTime(date);
    setShowAppointmentModal(true);
  }, []);

  // ── Modal: submit new appointment ──────────────────────────────────────
  const handleAppointmentSubmit = useCallback(
    async (data: AppointmentSubmitData) => {
      const appointment = await createAppointment({
        patient_id: data.patient_id,
        scheduled_at: new Date(data.scheduled_at),
        appointment_type: data.appointment_type,
        estimated_duration: data.estimated_duration,
        reason: data.reason,
      });

      setPendingWorkflowData({ patient_id: data.patient_id, appointment });
    },
    [createAppointment],
  );

  // ── Modal: after submit – optionally start workflow now ────────────────
  const handleAfterAppointmentSubmit = useCallback(async () => {
    setShowAppointmentModal(false);

    if (!pendingWorkflowData) return;

    const { patient_id, appointment } = pendingWorkflowData;
    setPendingWorkflowData(null);

    const appointmentTime = new Date(appointment.scheduled_at);
    const now = new Date();
    const currentHourStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours(), 0, 0);
    const currentHourEnd = new Date(currentHourStart.getTime() + 60 * 60 * 1000);
    const isWithinCurrentHour = appointmentTime >= currentHourStart && appointmentTime < currentHourEnd;

    if (isWithinCurrentHour) {
      const confirmed = await confirmDialog({
        title: '¿Iniciar consulta ahora?',
        text: 'La cita está programada para esta hora. ¿Deseas iniciar la consulta ahora?',
        confirmText: 'Sí, iniciar',
        cancelText: 'No, solo crear',
        icon: 'question',
      });

      if (confirmed) {
        startWorkflowWithAppointment(patient_id, appointment);
      }
    }
  }, [pendingWorkflowData, startWorkflowWithAppointment]);

  // ── Back to calendar ───────────────────────────────────────────────────
  const handleBackToCalendar = useCallback(() => {
    setSelectedPatient(null);
    setActiveAppointment(null);
    resetWorkflow();
  }, [setSelectedPatient, resetWorkflow]);

  return {
    activeAppointment,
    showAppointmentModal,
    setShowAppointmentModal,
    selectedSlotTime,
    handleSelectAppointment,
    handleCreateAppointment,
    handleAppointmentSubmit,
    handleAfterAppointmentSubmit,
    handleBackToCalendar,
  };
}
