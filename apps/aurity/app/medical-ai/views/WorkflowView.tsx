/**
 * WorkflowView
 *
 * Active consultation view — shown when a doctor has selected
 * an appointment and is working through the medical workflow steps.
 */

'use client';

import { useState } from 'react';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { NeuralNetworkCanvas } from '@/components/background/NeuralNetworkCanvas';
import { Calendar } from 'lucide-react';
import { WorkflowStep, Encounter } from '@aurity-standalone/types/medical';
import type { Appointment } from '@/components/bryntum/utils/appointment-transform.utils';
import type { Patient } from '@aurity-standalone/types/medical';

import { MedicalWorkflowSteps } from '../WorkflowSteps';
import { WorkflowStepsBar } from '../components/WorkflowStepsBar';

// ============================================================================
// Types
// ============================================================================

interface WorkflowViewProps {
  // Patient / appointment context
  selectedPatient: Patient | null;
  activeAppointment: Appointment;

  // Display values
  clinicName: string;
  doctorDisplayName: string;
  appointmentTimeDisplay: string | null;
  timeElapsed: string;
  isExistingSession: boolean;
  sessionDuration: string;

  // Workflow state
  currentStep: WorkflowStep;
  setCurrentStep: (step: WorkflowStep) => void;
  completedSteps: Set<string>;
  progress: number;
  isRecording: boolean;
  setIsRecording: (v: boolean) => void;

  // Workflow navigation
  goToNextStep: () => void;
  goToPreviousStep: () => void;

  // Session
  currentSessionId: string | null;
  setCurrentSessionId: (id: string) => void;

  // Actions
  onBackToCalendar: () => void;
}

// ============================================================================
// Component
// ============================================================================

export function WorkflowView({
  selectedPatient,
  activeAppointment,
  clinicName,
  doctorDisplayName,
  appointmentTimeDisplay,
  timeElapsed,
  isExistingSession,
  sessionDuration,
  currentStep,
  setCurrentStep,
  completedSteps,
  progress,
  isRecording,
  setIsRecording,
  goToNextStep,
  goToPreviousStep,
  currentSessionId,
  setCurrentSessionId,
  onBackToCalendar,
}: WorkflowViewProps) {
  const [encounterData] = useState<Partial<Encounter> | null>(null);

  return (
    <ProtectedRoute requireRoles={['FI-clinician', 'FI-superadmin']}>
      <AppTemplate
        headerConfig={{
          showBackButton: false,
          icon: 'stethoscope',
          iconColor: 'text-emerald-400',
          title: selectedPatient?.name || 'Consulta',
          subtitle: `${selectedPatient?.age || '?'} años · ${activeAppointment.reason || 'Consulta médica'}`,
          metrics: [
            { icon: 'building2', label: '', value: clinicName },
            { icon: 'user', label: '', value: doctorDisplayName },
            ...(appointmentTimeDisplay
              ? [{ icon: 'calendar' as const, label: '', value: appointmentTimeDisplay }]
              : []),
            {
              icon: 'clock' as const,
              label: '',
              value: isExistingSession && sessionDuration ? sessionDuration : timeElapsed,
              variant: 'primary' as const,
            },
          ],
          actions: (
            <button onClick={onBackToCalendar} className="med-back-btn">
              <Calendar className="w-4 h-4" />
              Volver al Calendario
            </button>
          ),
        }}
        padding="0"
        showWatermark={true}
        showGeometricBg={true}
      >
        <NeuralNetworkCanvas opacity={0.15} />

        <WorkflowStepsBar
          currentStep={currentStep}
          completedSteps={completedSteps}
          progress={progress}
          onStepClick={setCurrentStep}
        />

        {/* Step Content */}
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
