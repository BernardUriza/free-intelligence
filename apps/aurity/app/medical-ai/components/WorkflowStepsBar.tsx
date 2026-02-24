/**
 * WorkflowStepsBar
 *
 * Horizontal step pills + progress bar shown during an active consultation.
 */

'use client';

import React from 'react';
import { CheckCircle2, ChevronRight } from 'lucide-react';
import { WorkflowStep } from '@aurity-standalone/types/medical';
import { MedicalWorkflowSteps } from '../WorkflowSteps';

interface WorkflowStepsBarProps {
  currentStep: WorkflowStep;
  completedSteps: Set<string>;
  progress: number;
  onStepClick: (step: WorkflowStep) => void;
}

export function WorkflowStepsBar({
  currentStep,
  completedSteps,
  progress,
  onStepClick,
}: WorkflowStepsBarProps) {
  return (
    <div className="border-b border-white/10 bg-slate-900/60 backdrop-blur-sm px-6 py-3">
      {/* Step Pills */}
      <div className="flex items-center gap-3 overflow-x-auto pb-2 custom-scrollbar max-w-7xl mx-auto">
        {MedicalWorkflowSteps.map((step, index) => {
          const Icon = step.icon;
          const isActive = step.id === currentStep;
          const isCompleted = completedSteps.has(step.id);

          return (
            <React.Fragment key={step.id}>
              <button
                onClick={() => onStepClick(step.id)}
                className={
                  isActive
                    ? 'med-workflow-step-active'
                    : isCompleted
                      ? 'med-workflow-step-completed'
                      : 'med-workflow-step'
                }
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
                <ChevronRight
                  className={`h-4 w-4 flex-shrink-0 ${isCompleted ? 'text-green-500' : 'text-slate-700'}`}
                />
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
          <div className="med-progress-gradient" style={{ width: `${progress}%` }} />
        </div>
      </div>
    </div>
  );
}
