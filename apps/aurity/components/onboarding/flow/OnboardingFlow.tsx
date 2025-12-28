"use client";

/**
 * Refactored Onboarding Flow Component
 *
 * Uses declarative orchestration with state machine
 */

import { AppTemplate } from "../../layout/AppTemplate";
import { useOnboardingFlow } from "../hooks/useOnboardingFlow";

export function OnboardingFlow() {
  const { context, status, callbacks, currentStepDef } = useOnboardingFlow();

  if (!currentStepDef) {
    return <div>Loading...</div>;
  }

  const StepComponent = currentStepDef.component;

  return (
    <AppTemplate>
      <div className="fi-page-container p-8">
        <StepComponent
          context={context}
          callbacks={callbacks}
          status={status}
        />
      </div>
    </AppTemplate>
  );
}