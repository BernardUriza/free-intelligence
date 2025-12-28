/**
 * CheckinFlow - Main Check-in Flow Component
 *
 * Card: FI-CHECKIN-001
 * Orchestrates the full check-in flow on patient's mobile device.
 */

'use client';

import type { CheckinFlowProps } from './types';
import { useCheckinFlow } from './hooks';
import {
  IdentificationStep,
  ConfirmIdentityStep,
  PendingActionsStep,
  SuccessStep,
  ProgressIndicator,
} from './components';

export function CheckinFlow({
  clinicId,
  clinicName = 'la clínica',
  onComplete,
  onCancel,
}: CheckinFlowProps) {
  const {
    state,
    formState,
    setIdentificationMethod,
    updateFormField,
    handleIdentify,
    handleConfirmIdentity,
    handleCompleteAction,
    handleSkipAction,
    handleCompleteCheckin,
    goToStep,
    canProceedFromActions,
  } = useCheckinFlow({ clinicId, onComplete });

  return (
    <div className="fi-page-container p-4">
      <div className="max-w-md mx-auto">
        {/* Logo/Header */}
        <div className="flex items-center justify-center gap-2 mb-8 pt-4">
          <div className="fi-icon-xl rounded-lg fi-bg-avatar-purple fi-flex-center">
            <span className="text-white font-bold">A</span>
          </div>
          <span className="fi-title">AURITY</span>
        </div>

        {/* Progress Indicator */}
        {state.step !== 'success' && <ProgressIndicator currentStep={state.step} />}

        {/* Content */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
          {state.step === 'identify' && (
            <IdentificationStep
              clinicName={clinicName}
              method={state.identificationMethod}
              formState={formState}
              error={state.error}
              isLoading={state.isLoading}
              onMethodChange={setIdentificationMethod}
              onFormChange={updateFormField}
              onSubmit={handleIdentify}
              onCancel={onCancel}
            />
          )}

          {state.step === 'confirm_identity' && (
            <ConfirmIdentityStep
              patientData={state.patientData}
              onConfirm={handleConfirmIdentity}
            />
          )}

          {state.step === 'pending_actions' && (
            <PendingActionsStep
              actions={state.pendingActions}
              error={state.error}
              isLoading={state.isLoading}
              canProceed={canProceedFromActions()}
              onCompleteAction={handleCompleteAction}
              onSkipAction={handleSkipAction}
              onBack={() => goToStep('confirm_identity')}
              onComplete={handleCompleteCheckin}
            />
          )}

          {state.step === 'success' && (
            <SuccessStep
              patientName={state.patientData?.patient?.full_name}
              onClose={onCancel}
            />
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-slate-600 mt-6">
          Powered by AURITY · Sistema On-Premise
        </p>
      </div>
    </div>
  );
}

export default CheckinFlow;
