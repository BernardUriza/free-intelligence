"use client";

/**
 * Medical AI Workflow - AURITY (REFACTORED v3)
 *
 * Composition root — wires hooks and view components together.
 * All business logic lives in dedicated hooks; all UI in view components.
 *
 * Calendar-first UX:
 * - Doctor sees appointments calendar as main view
 * - Click appointment  → start workflow
 * - Click empty slot   → create appointment → start workflow
 */

import { useState, useCallback } from 'react';
import { useEncounterTimer } from '@/hooks/useEncounterTimer';
import { useCurrentDoctor } from '@/hooks/useCurrentDoctor';
import { useRBAC } from '@/hooks/useRBAC';
import { usePatientManagement, useSessionManagement } from '@aurity-standalone/medical';
import type { DoctorSaveData } from '@/components/admin/clinics/DoctorDetailModal';

import { useDoctorAppointments } from './hooks/useDoctorAppointments';
import { useClinicManagement } from './hooks/useClinicManagement';
import { useWorkflowState } from './hooks/useWorkflowState';
import { useAppointmentActions } from './hooks/useAppointmentActions';
import { useDerivedDisplayValues } from './hooks/useDerivedDisplayValues';

import { CalendarView } from './views/CalendarView';
import { WorkflowView } from './views/WorkflowView';

export default function MedicalAIWorkflow() {
  // ── Domain hooks ─────────────────────────────────────────────────────
  const { doctor, membership, updateDoctorProfile } = useCurrentDoctor();
  const { isSuperAdmin } = useRBAC();
  const isClinicAdmin = isSuperAdmin;

  const {
    patients,
    patientsError,
    showPatientModal,
    setShowPatientModal,
    editingPatient,
    setEditingPatient,
    selectedPatient,
    setSelectedPatient,
    handleStartNewConsultation,
  } = usePatientManagement();

  const {
    currentSessionId,
    setCurrentSessionId,
    isExistingSession,
    setIsExistingSession,
    sessionDuration,
    setSessionDuration,
    deleteConfirmSession,
    setDeleteConfirmSession,
    deletingSession,
    handleDeleteSession,
  } = useSessionManagement();

  // ── Clinic / doctor selection (admin) ────────────────────────────────
  const {
    clinics,
    selectedClinicId,
    loadingClinics,
    clinicDoctors,
    loadingDoctors,
    effectiveClinicId,
    effectiveDoctor,
    handleSelectDoctor,
    handleSelectClinic,
  } = useClinicManagement({
    isSuperAdmin,
    isClinicAdmin,
    membershipClinicId: membership?.clinic_id,
    currentDoctor: doctor,
  });

  // ── Appointments ─────────────────────────────────────────────────────
  const {
    appointments,
    loading: loadingAppointments,
    currentDate,
    setCurrentDate,
    createAppointment,
    startAppointment,
  } = useDoctorAppointments(effectiveDoctor?.doctor_id, effectiveClinicId ?? undefined);

  // ── Workflow state ───────────────────────────────────────────────────
  const {
    currentStep,
    setCurrentStep,
    isRecording,
    setIsRecording,
    completedSteps,
    progress,
    goToNextStep,
    goToPreviousStep,
    resetWorkflow,
  } = useWorkflowState();

  // ── Appointment actions ──────────────────────────────────────────────
  const {
    activeAppointment,
    showAppointmentModal,
    setShowAppointmentModal,
    selectedSlotTime,
    handleSelectAppointment,
    handleCreateAppointment,
    handleAppointmentSubmit,
    handleAfterAppointmentSubmit,
    handleBackToCalendar,
  } = useAppointmentActions({
    patients,
    startAppointment,
    createAppointment,
    handleStartNewConsultation,
    setIsExistingSession,
    setSessionDuration,
    resetWorkflow,
    setSelectedPatient,
  });

  // ── Display values ───────────────────────────────────────────────────
  const { appointmentTimeDisplay, clinicName, doctorDisplayName } = useDerivedDisplayValues({
    effectiveDoctor,
    activeAppointment,
    isSuperAdmin,
    selectedClinicId,
    clinics,
    membershipClinicName: membership?.clinic_name,
  });

  // ── Encounter timer ──────────────────────────────────────────────────
  const isNewConsultation = Boolean(selectedPatient && !isExistingSession);
  const { timeElapsed } = useEncounterTimer(isNewConsultation);

  // ── Doctor availability modal ────────────────────────────────────────
  const [showDoctorModal, setShowDoctorModal] = useState(false);
  const [auditSessionId, setAuditSessionId] = useState<string | null>(null);

  const handleSaveDoctorAvailability = useCallback(async (data: DoctorSaveData) => {
    await updateDoctorProfile(data);
    setShowDoctorModal(false);
  }, [updateDoctorProfile]);

  // ── Render ───────────────────────────────────────────────────────────
  if (!activeAppointment) {
    return (
      <CalendarView
        doctor={doctor}
        membership={membership}
        effectiveDoctor={effectiveDoctor}
        isSuperAdmin={isSuperAdmin}
        isClinicAdmin={isClinicAdmin}
        clinics={clinics}
        selectedClinicId={selectedClinicId}
        loadingClinics={loadingClinics}
        clinicDoctors={clinicDoctors}
        loadingDoctors={loadingDoctors}
        onSelectClinic={handleSelectClinic}
        onSelectDoctor={handleSelectDoctor}
        appointments={appointments}
        currentDate={currentDate}
        onDateChange={setCurrentDate}
        loadingAppointments={loadingAppointments}
        onSelectAppointment={handleSelectAppointment}
        onCreateAppointment={handleCreateAppointment}
        showAppointmentModal={showAppointmentModal}
        onCloseAppointmentModal={() => setShowAppointmentModal(false)}
        onSubmitAppointment={handleAppointmentSubmit}
        onAfterSubmitAppointment={handleAfterAppointmentSubmit}
        selectedSlotTime={selectedSlotTime}
        patientsError={patientsError}
        showPatientModal={showPatientModal}
        setShowPatientModal={setShowPatientModal}
        editingPatient={editingPatient}
        setEditingPatient={setEditingPatient}
        deleteConfirmSession={deleteConfirmSession}
        setDeleteConfirmSession={setDeleteConfirmSession}
        deletingSession={deletingSession}
        handleDeleteSession={handleDeleteSession}
        showDoctorModal={showDoctorModal}
        setShowDoctorModal={setShowDoctorModal}
        onSaveDoctorAvailability={handleSaveDoctorAvailability}
        auditSessionId={auditSessionId}
        setAuditSessionId={setAuditSessionId}
      />
    );
  }

  return (
    <WorkflowView
      selectedPatient={selectedPatient}
      activeAppointment={activeAppointment}
      clinicName={clinicName}
      doctorDisplayName={doctorDisplayName}
      appointmentTimeDisplay={appointmentTimeDisplay}
      timeElapsed={timeElapsed}
      isExistingSession={isExistingSession}
      sessionDuration={sessionDuration}
      currentStep={currentStep}
      setCurrentStep={setCurrentStep}
      completedSteps={completedSteps}
      progress={progress}
      isRecording={isRecording}
      setIsRecording={setIsRecording}
      goToNextStep={goToNextStep}
      goToPreviousStep={goToPreviousStep}
      currentSessionId={currentSessionId}
      setCurrentSessionId={setCurrentSessionId}
      onBackToCalendar={handleBackToCalendar}
    />
  );
}
