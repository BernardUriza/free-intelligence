"use client";

/**
 * Medical AI Workflow - AURITY (REFACTORED v2)
 *
 * Production medical consultation workflow with AI-powered transcription
 * PROTECTED ROUTE: Requires Auth0 authentication + MEDICO or ADMIN role
 *
 * REFACTORED v2: Calendar-first UX
 * - Doctor sees appointments calendar as main view
 * - Click appointment → start workflow
 * - Click empty slot → create appointment → start workflow
 */

import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { medicalAiHeader } from '@/config/page-headers';
import { PatientModal } from '@/components/patients';
import { SessionAuditPanel } from '@/components/medical';
import { AlertCircle, CheckCircle2, ChevronRight, Trash2, Calendar } from 'lucide-react';
import { useEncounterTimer } from '@/hooks/useEncounterTimer';
import { WorkflowStep, Encounter } from '@aurity-standalone/types/medical';
import { DoctorDetailModal, type DoctorSaveData } from '@/components/admin/clinics/DoctorDetailModal';
import type { Appointment } from '@/components/bryntum/utils/appointment-transform.utils';

// Modular imports
import { MedicalWorkflowSteps } from './WorkflowSteps';
import { usePatientManagement } from './usePatientManagement';
import { useSessionManagement } from './useSessionManagement';
import { useCurrentDoctor } from './useCurrentDoctor';
import { useDoctorAppointments } from './hooks/useDoctorAppointments';
import { useClinicDoctors } from './hooks/useClinicDoctors';
import { DoctorAppointmentsCalendar } from './components/DoctorAppointmentsCalendar';
import { AppointmentModal } from '@/components/appointments';
import { DoctorSelector } from './components/DoctorSelector';
import { ClinicSelector } from './components/ClinicSelector';
import { useRBAC, ROLES } from '@/hooks/useRBAC';
import { fetchClinics, type Doctor, type Clinic } from '@/lib/api/clinics';
import { confirmDialog } from '@/lib/swal';

export default function MedicalAIWorkflow() {
  // Patient management (custom hook)
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
    handleEditPatient,
  } = usePatientManagement();

  // Session management (custom hook)
  const {
    sessions,
    loadingSessions,
    currentSessionId,
    setCurrentSessionId,
    isExistingSession,
    setIsExistingSession,
    sessionDuration,
    setSessionDuration,
    copiedSessionId,
    deleteConfirmSession,
    setDeleteConfirmSession,
    deletingSession,
    sessionStatuses,
    handleDeleteSession,
    handleSelectSession,
    handleCopySessionId,
  } = useSessionManagement();

  // UI state
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('escuchar');
  const [isRecording, setIsRecording] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [encounterData] = useState<Partial<Encounter> | null>(null);

  // Audit panel state
  const [auditSessionId, setAuditSessionId] = useState<string | null>(null);

  // Doctor availability modal
  const { doctor, membership, updateDoctorProfile } = useCurrentDoctor();
  const [showDoctorModal, setShowDoctorModal] = useState(false);

  // RBAC for admin features
  const { isSuperAdmin, hasRole } = useRBAC();
  const isClinicAdmin = isSuperAdmin || hasRole(ROLES.ADMIN);

  // Clinics (for superadmin clinic selector)
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [selectedClinicId, setSelectedClinicId] = useState<string | null>(null);
  const [loadingClinics, setLoadingClinics] = useState(false);

  // Fetch all clinics for superadmin
  useEffect(() => {
    if (!isSuperAdmin) {
      setClinics([]);
      return;
    }

    let cancelled = false;
    setLoadingClinics(true);

    fetchClinics()
      .then((data) => {
        if (cancelled) return;
        console.log('[MedicalAI] Fetched clinics:', data);
        setClinics(data);
        // Default to membership clinic if available, else first clinic
        setSelectedClinicId((prev) =>
          prev || membership?.clinic_id || data[0]?.clinic_id || null
        );
      })
      .catch((err) => {
        if (!cancelled) {
          console.error('[MedicalAI] Error fetching clinics:', err);
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingClinics(false);
      });

    return () => { cancelled = true; };
  }, [isSuperAdmin, membership?.clinic_id]);

  // Effective clinic ID (superadmin can switch, others use their membership)
  const effectiveClinicId = isSuperAdmin ? selectedClinicId : membership?.clinic_id;

  // Clinic doctors (for admin selector) - uses effectiveClinicId
  const { doctors: clinicDoctors, loading: loadingDoctors } = useClinicDoctors(
    isClinicAdmin ? (effectiveClinicId ?? undefined) : undefined
  );

  // Selected doctor for calendar (admin can switch, doctor sees their own)
  const [selectedDoctorId, setSelectedDoctorId] = useState<string | null>(null);

  // Effective doctor for calendar view
  const effectiveDoctor = useMemo(() => {
    if (isClinicAdmin && selectedDoctorId) {
      return clinicDoctors.find(d => d.doctor_id === selectedDoctorId) || null;
    }
    return doctor;
  }, [isClinicAdmin, selectedDoctorId, clinicDoctors, doctor]);

  // Initialize selected doctor to current doctor
  useEffect(() => {
    if (doctor && !selectedDoctorId) {
      setSelectedDoctorId(doctor.doctor_id);
    }
  }, [doctor, selectedDoctorId]);

  // Handle doctor selection (admin only)
  const handleSelectDoctor = useCallback((selected: Doctor) => {
    setSelectedDoctorId(selected.doctor_id);
  }, []);

  // Handle clinic selection (superadmin only)
  const handleSelectClinic = useCallback((selected: Clinic) => {
    setSelectedClinicId(selected.clinic_id);
    setSelectedDoctorId(null); // Reset doctor when clinic changes
  }, []);

  // Appointments calendar state (NEW - Calendar-first UX)
  const [activeAppointment, setActiveAppointment] = useState<Appointment | null>(null);
  const [showAppointmentModal, setShowAppointmentModal] = useState(false);
  const [selectedSlotTime, setSelectedSlotTime] = useState<Date | null>(null);
  // Track created appointment for workflow start
  const [pendingWorkflowData, setPendingWorkflowData] = useState<{
    patient_id: string;
    appointment: Appointment;
  } | null>(null);

  // Doctor appointments hook (uses effectiveDoctor for admin switching)
  const {
    appointments,
    loading: loadingAppointments,
    currentDate,
    setCurrentDate,
    createAppointment,
    startAppointment,
  } = useDoctorAppointments(effectiveDoctor?.doctor_id, effectiveClinicId ?? undefined);

  // Handle doctor availability save
  const handleSaveDoctorAvailability = useCallback(async (data: DoctorSaveData) => {
    await updateDoctorProfile(data);
    setShowDoctorModal(false);
  }, [updateDoctorProfile]);

  // Real-time encounter timer (only for new consultations)
  const isNewConsultation = Boolean(selectedPatient && !isExistingSession);
  const { timeElapsed } = useEncounterTimer(isNewConsultation);

  const currentStepIndex = MedicalWorkflowSteps.findIndex(step => step.id === currentStep);

  // Workflow header display values (must be before any early returns)
  const appointmentTimeDisplay = useMemo(() => {
    if (!activeAppointment?.scheduled_at) return null;
    const date = new Date(activeAppointment.scheduled_at);
    return date.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', hour12: true });
  }, [activeAppointment?.scheduled_at]);

  const clinicName = useMemo(() => {
    if (isSuperAdmin && selectedClinicId) {
      return clinics.find(c => c.clinic_id === selectedClinicId)?.name || 'Clínica';
    }
    return membership?.clinic_name || 'Clínica';
  }, [isSuperAdmin, selectedClinicId, clinics, membership?.clinic_name]);

  const doctorDisplayName = useMemo(() => {
    return effectiveDoctor?.display_name ||
           (effectiveDoctor ? `${effectiveDoctor.nombre} ${effectiveDoctor.apellido}` : 'Doctor');
  }, [effectiveDoctor]);
  const progress = ((currentStepIndex + 1) / MedicalWorkflowSteps.length) * 100;

  // Extract medical keywords from session preview
  const extractMedicalInfo = (preview: string): string[] => {
    const medicalKeywords = [
      'hipertensión', 'diabetes', 'asma', 'artritis', 'migraña',
      'alergia', 'penicilina', 'dolor', 'fiebre', 'tos',
      'gripe', 'covid', 'presión', 'glucosa', 'colesterol'
    ];

    const found = new Set<string>();
    const lowerPreview = preview.toLowerCase();

    medicalKeywords.forEach(keyword => {
      if (lowerPreview.includes(keyword)) {
        found.add(keyword.charAt(0).toUpperCase() + keyword.slice(1));
      }
    });

    return Array.from(found).slice(0, 3);
  };

  // Calculate session counts per patient
  const sessionCounts = useMemo(() => {
    const counts: Record<string, number> = {};

    sessions.forEach(session => {
      const patientName = session.patient_name;
      if (patientName && patientName !== 'Paciente') {
        const matchingPatient = patients.find(p => p.name === patientName);
        if (matchingPatient) {
          counts[matchingPatient.id] = (counts[matchingPatient.id] || 0) + 1;
        }
      }
    });

    return counts;
  }, [sessions, patients]);

  // Workflow navigation
  const goToNextStep = () => {
    if (currentStepIndex < MedicalWorkflowSteps.length - 1) {
      setCompletedSteps(prev => new Set([...Array.from(prev), currentStep]));
      setCurrentStep(MedicalWorkflowSteps[currentStepIndex + 1].id);
    }
  };

  const goToPreviousStep = () => {
    if (currentStepIndex > 0) {
      setCurrentStep(MedicalWorkflowSteps[currentStepIndex - 1].id);
    }
  };

  // Handle appointment selection from calendar
  const handleSelectAppointment = useCallback(async (appointment: Appointment) => {
    // Find patient from appointment
    const patient = patients.find(p => p.id === appointment.patient_id);
    if (!patient) {
      console.error('[MedicalAI] Patient not found for appointment:', appointment.patient_id);
      return;
    }

    // Mark appointment as in_progress
    try {
      await startAppointment(appointment.appointment_id);
    } catch (error) {
      console.error('[MedicalAI] Failed to start appointment:', error);
    }

    // Start workflow with this patient
    handleStartNewConsultation(patient);
    setActiveAppointment(appointment);
    setIsExistingSession(false);
    setSessionDuration('');
    setCurrentStep('escuchar');
    setCompletedSteps(new Set());
  }, [patients, startAppointment, handleStartNewConsultation, setIsExistingSession, setSessionDuration]);

  // Handle creating appointment from calendar slot click
  const handleCreateAppointment = useCallback((date: Date) => {
    setSelectedSlotTime(date);
    setShowAppointmentModal(true);
  }, []);

  // Handle appointment modal submit (unified modal)
  const handleAppointmentSubmit = useCallback(async (data: {
    patient_id: string;
    doctor_id: string;
    scheduled_at: string;
    appointment_type: string;
    estimated_duration: number;
    reason: string;
    notes?: string;
  }) => {
    // Create appointment via API
    const appointment = await createAppointment({
      patient_id: data.patient_id,
      scheduled_at: new Date(data.scheduled_at),
      appointment_type: data.appointment_type,
      estimated_duration: data.estimated_duration,
      reason: data.reason,
    });

    // Store for onAfterSubmit to use
    setPendingWorkflowData({
      patient_id: data.patient_id,
      appointment,
    });
  }, [createAppointment]);

  // Start workflow helper
  const startWorkflowWithAppointment = useCallback((patientId: string, appointment: Appointment) => {
    const patient = patients.find(p => p.id === patientId);
    if (patient) {
      handleStartNewConsultation(patient);
      setActiveAppointment(appointment);
      setIsExistingSession(false);
      setSessionDuration('');
      setCurrentStep('escuchar');
      setCompletedSteps(new Set());
    }
  }, [patients, handleStartNewConsultation, setIsExistingSession, setSessionDuration]);

  // Handle after appointment submit - ask to start if within current hour
  const handleAfterAppointmentSubmit = useCallback(async () => {
    setShowAppointmentModal(false);

    if (!pendingWorkflowData) return;

    const { patient_id, appointment } = pendingWorkflowData;
    setPendingWorkflowData(null);

    // Check if appointment is within current hour
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

  // Handle returning to calendar view
  const handleBackToCalendar = useCallback(() => {
    setSelectedPatient(null);
    setActiveAppointment(null);
    setCurrentStep('escuchar');
    setCompletedSteps(new Set());
  }, [setSelectedPatient]);

  // Calendar View (main view - no active appointment)
  if (!activeAppointment) {
    const headerConfig = medicalAiHeader({ subtitle: 'Mis citas de hoy' });

    return (
      <AppTemplate
        headerConfig={headerConfig}
        headerActions={
          doctor && membership && (
            <Button
              onClick={() => setShowDoctorModal(true)}
              variant="outline"
              size="sm"
              icon={Calendar}
            >
              Mi Disponibilidad
            </Button>
          )
        }
        padding="0"
        showWatermark={true}
        showGeometricBg={true}
      >
        <div className="max-w-7xl mx-auto px-6 py-8">
          {/* Error Loading Patients */}
          {patientsError && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3">
              <AlertCircle className="h-5 w-5 fi-text-error flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-red-300">Error al cargar pacientes</p>
                <p className="text-sm fi-text-error mt-1">{patientsError}</p>
              </div>
            </div>
          )}

          {/* Clinic Selector (Superadmin only) + Doctor Selector (Admin only) */}
          {isClinicAdmin && (
            <div className="mb-4 flex items-center gap-3 flex-wrap">
              {/* Clinic Selector - only for superadmin */}
              {isSuperAdmin && (
                <>
                  <span className="text-sm text-slate-400">Clínica:</span>
                  <ClinicSelector
                    clinics={clinics}
                    selectedClinic={clinics.find(c => c.clinic_id === selectedClinicId) || null}
                    onSelectClinic={handleSelectClinic}
                    loading={loadingClinics}
                  />
                </>
              )}
              {/* Doctor Selector - for all admins */}
              {clinicDoctors.length > 0 && (
                <>
                  <span className="text-sm text-slate-400">Doctor:</span>
                  <DoctorSelector
                    doctors={clinicDoctors}
                    selectedDoctor={effectiveDoctor}
                    onSelectDoctor={handleSelectDoctor}
                    loading={loadingDoctors}
                  />
                </>
              )}
            </div>
          )}

          {/* Doctor Appointments Calendar */}
          {effectiveDoctor ? (
            <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-6 shadow-xl h-[calc(100vh-220px)]">
              <DoctorAppointmentsCalendar
                appointments={appointments}
                currentDate={currentDate}
                onDateChange={setCurrentDate}
                onSelectAppointment={handleSelectAppointment}
                onCreateAppointment={handleCreateAppointment}
                loading={loadingAppointments || loadingDoctors}
                availability={effectiveDoctor?.working_hours}
              />
            </div>
          ) : (
            <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-12 shadow-xl flex items-center justify-center h-[calc(100vh-220px)]">
              <p className="text-slate-400 text-lg">Selecciona un doctor para ver su calendario</p>
            </div>
          )}

          {/* Unified Appointment Modal */}
          <AppointmentModal
            mode="create"
            isOpen={showAppointmentModal}
            onClose={() => setShowAppointmentModal(false)}
            onCancel={() => setShowAppointmentModal(false)}
            onSubmit={handleAppointmentSubmit}
            doctors={isClinicAdmin && clinicDoctors.length > 0
              ? clinicDoctors as any[]
              : effectiveDoctor ? [effectiveDoctor as any] : []}
            prefilledData={{
              date: selectedSlotTime || undefined,
              doctorId: effectiveDoctor?.doctor_id,
            }}
            submitButtonText="Crear Cita"
            hideDoctorField={!isClinicAdmin}
            onAfterSubmit={handleAfterAppointmentSubmit}
          />

          {/* Patient Creation/Edit Modal */}
          <PatientModal
            isOpen={showPatientModal || editingPatient !== null}
            mode={editingPatient ? 'edit' : 'create'}
            patient={editingPatient || undefined}
            initialData={editingPatient ? {
              nombre: editingPatient.name.split(' ')[0],
              apellido: editingPatient.name.split(' ').slice(1).join(' '),
              fecha_nacimiento: editingPatient.fechaNacimiento,
              curp: editingPatient.curp || null,
            } : undefined}
            onClose={() => {
              setShowPatientModal(false);
              setEditingPatient(null);
            }}
            onSuccess={() => {
              // Handled by usePatientManagement internally
              setShowPatientModal(false);
              setEditingPatient(null);
            }}
          />

          {/* Delete Confirmation Modal */}
          {deleteConfirmSession && (
            <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 max-w-md w-full shadow-2xl">
                <div className="flex items-start gap-4 mb-4">
                  <div className="w-12 h-12 bg-red-500/20 rounded-xl flex items-center justify-center flex-shrink-0">
                    <Trash2 className="h-6 w-6 fi-text-error" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-white mb-1">Eliminar Sesión</h3>
                    <p className="fi-subtitle">
                      ¿Estás seguro de eliminar esta sesión? Esta acción no se puede deshacer.
                    </p>
                  </div>
                </div>

                <div className="bg-slate-900/50 rounded-lg p-3 mb-6">
                  <div className="fi-text-xs-muted mb-1">Session ID</div>
                  <div className="text-sm font-mono text-white">{deleteConfirmSession}</div>
                </div>

                <div className="flex gap-3">
                  <Button
                    onClick={() => setDeleteConfirmSession(null)}
                    disabled={deletingSession !== null}
                    variant="secondary"
                    fullWidth
                  >
                    Cancelar
                  </Button>
                  <Button
                    onClick={() => handleDeleteSession(deleteConfirmSession)}
                    disabled={deletingSession !== null}
                    variant="danger"
                    fullWidth
                    loading={deletingSession === deleteConfirmSession}
                  >
                    {deletingSession === deleteConfirmSession ? 'Eliminando...' : 'Eliminar Sesión'}
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Session Audit Panel (NEW) */}
          {auditSessionId && (
            <SessionAuditPanel
              sessionId={auditSessionId}
              isOpen={true}
              onClose={() => setAuditSessionId(null)}
              onApprove={() => {
                console.log('[MedicalAI] Session approved:', auditSessionId);
                // Refresh sessions list
              }}
              onReject={() => {
                console.log('[MedicalAI] Session rejected:', auditSessionId);
                // Refresh sessions list
              }}
            />
          )}

          {/* Doctor Availability Modal */}
          {showDoctorModal && doctor && (
            <DoctorDetailModal
              doctor={{
                id: doctor.doctor_id,
                doctor_id: doctor.doctor_id,
                name: doctor.display_name || `${doctor.nombre} ${doctor.apellido}`,
                display_name: doctor.display_name,
                specialty: doctor.especialidad || undefined,
                especialidad: doctor.especialidad,
                work_start_time: doctor.work_start_time,
                work_end_time: doctor.work_end_time,
                working_hours: doctor.working_hours,
                email: doctor.email,
                cedula_profesional: doctor.cedula_profesional,
              }}
              onClose={() => setShowDoctorModal(false)}
              onSave={handleSaveDoctorAvailability}
              mode="edit"
            />
          )}
        </div>
      </AppTemplate>
    );
  }

  // Workflow View (Patient selected, working on consultation)
  return (
    <ProtectedRoute requireRoles={['FI-doctor', 'FI-admin']}>
      <AppTemplate
        headerConfig={{
          showBackButton: false, // We use custom back button
          icon: 'stethoscope',
          iconColor: 'text-emerald-400',
          title: selectedPatient?.name || 'Consulta',
          subtitle: `${selectedPatient?.age || '?'} años · ${activeAppointment?.reason || 'Consulta médica'}`,
          metrics: [
            {
              icon: 'building2',
              label: '',
              value: clinicName,
            },
            {
              icon: 'user',
              label: '',
              value: doctorDisplayName,
            },
            ...(appointmentTimeDisplay ? [{
              icon: 'calendar' as const,
              label: '',
              value: appointmentTimeDisplay,
            }] : []),
            {
              icon: 'clock' as const,
              label: '',
              value: isExistingSession && sessionDuration ? sessionDuration : timeElapsed,
              variant: 'primary' as const,
            },
          ],
          actions: (
            <button
              onClick={handleBackToCalendar}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-sm rounded-lg transition-all border border-slate-700 hover:border-slate-600 flex items-center gap-2"
            >
              <Calendar className="w-4 h-4" />
              Volver al Calendario
            </button>
          ),
        }}
        padding="0"
        showWatermark={true}
        showGeometricBg={true}
      >

        {/* Workflow Steps Bar */}
        <div className="border-b border-slate-800/50 bg-slate-900/60 px-6 py-3">
          {/* Workflow Steps - Pills */}
          <div className="flex items-center gap-3 overflow-x-auto pb-2 custom-scrollbar max-w-7xl mx-auto">
            {MedicalWorkflowSteps.map((step, index) => {
              const Icon = step.icon;
              const isActive = step.id === currentStep;
              const isCompleted = completedSteps.has(step.id);

              return (
                <React.Fragment key={step.id}>
                  <button
                    onClick={() => setCurrentStep(step.id)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all whitespace-nowrap ${
                      isActive
                        ? 'bg-emerald-500/20 border-2 border-emerald-500/50 text-emerald-300 shadow-lg'
                        : isCompleted
                        ? 'bg-green-500/10 border border-green-500/30 text-green-300 hover:bg-green-500/20'
                        : 'bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:bg-slate-800 hover:border-slate-600'
                    }`}
                  >
                    {isCompleted ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : (
                      <Icon className="h-4 w-4" />
                    )}
                    <span className="text-sm font-semibold">{step.label}</span>
                    {isActive && (
                      <span className="ml-1 px-2 py-0.5 bg-emerald-500/30 rounded text-xs font-bold">
                        {index + 1}/{MedicalWorkflowSteps.length}
                      </span>
                    )}
                  </button>
                  {index < MedicalWorkflowSteps.length - 1 && (
                    <ChevronRight className={`h-4 w-4 flex-shrink-0 ${isCompleted ? 'text-green-500' : 'text-slate-700'}`} />
                  )}
                </React.Fragment>
              );
            })}
          </div>

          {/* Progress Bar */}
          <div className="mt-3 max-w-7xl mx-auto">
            <div className="flex items-center justify-between mb-1.5">
              <span className="fi-text-xs-medium text-slate-400">Progreso de consulta</span>
              <span className="text-xs font-bold fi-text-success">{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-gradient-to-r from-emerald-500 to-cyan-500 h-2 rounded-full transition-all duration-500 shadow-lg"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>

        {/* Main Content */}
        <main className="p-6">
          <div className="max-w-7xl mx-auto">
            {MedicalWorkflowSteps.map((step) => {
              const StepComponent = step.component;
              const isActive = step.id === currentStep;
              const isCapture = step.id === 'escuchar';

              if (!isCapture && !isActive && !completedSteps.has(step.id)) {
                return null;
              }

              return (
                <div
                  key={step.id}
                  style={{ display: isActive ? 'block' : 'none' }}
                  className="animate-fade-in"
                >
                  <StepComponent
                    onNext={goToNextStep}
                    onPrevious={goToPreviousStep}
                    isRecording={isRecording}
                    setIsRecording={setIsRecording}
                    encounterData={encounterData || undefined}
                    patient={selectedPatient || undefined}
                    sessionId={currentSessionId}
                    onSessionCreated={setCurrentSessionId}
                    readOnly={isExistingSession}
                  />
                </div>
              );
            })}
          </div>
        </main>
      </AppTemplate>
    </ProtectedRoute>
  );
}
