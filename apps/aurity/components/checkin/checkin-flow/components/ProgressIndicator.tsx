'use client';

/**
 * ProgressIndicator Component
 *
 * Visual step progress for the check-in flow.
 */

import type { CheckinStep } from '@aurity-standalone/types/checkin';

interface ProgressIndicatorProps {
  currentStep: CheckinStep;
}

const STEPS: CheckinStep[] = ['identify', 'confirm_identity', 'pending_actions'];

export function ProgressIndicator({ currentStep }: ProgressIndicatorProps) {
  const currentIndex = STEPS.indexOf(currentStep);

  return (
    <div className="flex items-center justify-center gap-2 mb-8">
      {STEPS.map((step, index) => {
        const isActive = currentStep === step;
        const isComplete = currentIndex > index;

        return (
          <div key={step} className="flex items-center">
            <div
              className={
                isActive
                  ? 'fi-step-circle-active'
                  : isComplete
                  ? 'fi-step-circle-complete'
                  : 'fi-step-circle'
              }
            >
              {index + 1}
            </div>
            {index < STEPS.length - 1 && (
              <div className={isComplete ? 'fi-step-connector-complete' : 'fi-step-connector'} />
            )}
          </div>
        );
      })}
    </div>
  );
}
