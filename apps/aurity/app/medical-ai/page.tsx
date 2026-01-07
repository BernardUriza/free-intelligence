"use client";

/**
 * Medical AI Workflow - AURITY (REFACTORED)
 *
 * Production medical consultation workflow with AI-powered transcription
 * PROTECTED ROUTE: Requires Auth0 authentication + MEDICO or ADMIN role
 *
 * REFACTORED: Modular architecture with custom hooks
 * - usePatientManagement: Patient state
 * - useSessionManagement: Session state
 * - WorkflowSteps: Workflow configuration
 */

import React, { useState, useMemo, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { medicalAiHeader } from '@/config/page-headers';
import { PatientSelector, PatientModal } from '@/components/patients';
import { SessionAuditPanel } from '@/components/medical';
import { AlertCircle, CheckCircle2, ChevronRight, Trash2, Calendar } from 'lucide-react';
import { useEncounterTimer } from '@/hooks/useEncounterTimer';
import { WorkflowStep, Encounter } from '@aurity-standalone/types/medical';
import { DoctorDetailModal, type DoctorSaveData } from '@/components/admin/clinics/DoctorDetailModal';

// Modular imports
import { MedicalWorkflowSteps } from './WorkflowSteps';
import { usePatientManagement } from './usePatientManagement';
import { useSessionManagement } from './useSessionManagement';
import { useCurrentDoctor } from './useCurrentDoctor';

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
  const [showPatientSelector, setShowPatientSelector] = useState(true);
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('escuchar');
  const [isRecording, setIsRecording] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [encounterData] = useState<Partial<Encounter> | null>(null);

  // Audit panel state (NEW)
  const [auditSessionId, setAuditSessionId] = useState<string | null>(null);

  // Doctor availability modal
  const { doctor, membership, updateDoctorProfile } = useCurrentDoctor();
  const [showDoctorModal, setShowDoctorModal] = useState(false);

  // Handle doctor availability save
  const handleSaveDoctorAvailability = useCallback(async (data: DoctorSaveData) => {
    await updateDoctorProfile(data);
    setShowDoctorModal(false);
  }, [updateDoctorProfile]);

  // Real-time encounter timer (only for new consultations)
  const isNewConsultation = Boolean(selectedPatient && !isExistingSession);
  const { timeElapsed } = useEncounterTimer(isNewConsultation);

  const currentStepIndex = MedicalWorkflowSteps.findIndex(step => step.id === currentStep);
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

  // Handle patient selection and session start
  const handlePatientSelected = (patient: any) => {
    handleStartNewConsultation(patient);
    setIsExistingSession(false);
    setSessionDuration('');
    setShowPatientSelector(false);
    setCurrentStep('escuchar');
    setCompletedSteps(new Set());
  };

  // Handle existing session selection
  const handleExistingSessionSelected = (sessionId: string) => {
    handleSelectSession(sessionId);
    setShowPatientSelector(false);
    setCurrentStep('escuchar');
  };

  // Patient Selector View
  if (showPatientSelector) {
    const headerConfig = medicalAiHeader({ subtitle: 'Selecciona un paciente para iniciar' });

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

          {/* Patient & Session Selector */}
          <PatientSelector
            patients={patients}
            sessions={sessions}
            sessionStatuses={sessionStatuses}
            sessionCounts={sessionCounts}
            onSelectPatient={handlePatientSelected}
            onEditPatient={handleEditPatient}
            onSelectSession={handleExistingSessionSelected}
            onDeleteSession={(sessionId) => setDeleteConfirmSession(sessionId)}
            onCopySessionId={handleCopySessionId}
            onAuditSession={(sessionId) => setAuditSessionId(sessionId)} // NEW
            copiedSessionId={copiedSessionId}
            loadingSessions={loadingSessions}
            extractMedicalInfo={extractMedicalInfo}
            onAddPatient={() => setShowPatientModal(true)}
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
  const workflowHeaderConfig = medicalAiHeader({
    subtitle: selectedPatient ? `${selectedPatient.name}, ${selectedPatient.age} años` : 'Consulta médica con IA',
  });

  return (
    <ProtectedRoute requireRoles={['FI-doctor', 'FI-admin']}>
      <AppTemplate
        headerConfig={{
          ...workflowHeaderConfig,
          metrics: [
            {
              icon: 'clock',
              label: '',
              value: isExistingSession && sessionDuration ? sessionDuration : timeElapsed,
              variant: 'primary'
            }
          ],
          actions: (
            <button
              onClick={() => {
                setSelectedPatient(null);
                setShowPatientSelector(true);
              }}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-sm rounded-lg transition-all border border-slate-700 hover:border-slate-600"
            >
              Cambiar Paciente
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
