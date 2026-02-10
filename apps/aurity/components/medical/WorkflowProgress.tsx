/**
 * WorkflowProgress Component
 *
 * Backend processing workflow progress indicator.
 *
 * Features:
 * - Progress bar with percentage
 * - Stage status grid (upload, transcribe, diarize, soap)
 * - Icons and animations
 * - Status indicators (pending, in_progress, completed, failed)
 *
 * Extracted from ConversationCapture (Phase 7)
 */

import { Loader2, Upload, Mic, Users, ClipboardList, Check, X } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface WorkflowStatus {
  job_id: string;
  session_id: string;
  status: string;
  progress_pct: number;
  stages: {
    upload: string;
    transcribe: string;
    diarize: string;
    soap: string;
  };
  soap_note?: any;
  result_data?: any;
  error?: string;
}

interface WorkflowProgressProps {
  workflowStatus: WorkflowStatus;
}

export function WorkflowProgress({ workflowStatus }: WorkflowProgressProps) {
  const stageConfig: Record<string, { icon: LucideIcon; label: string }> = {
    upload: { icon: Upload, label: 'Upload' },
    transcribe: { icon: Mic, label: 'Whisper' },
    diarize: { icon: Users, label: 'Speakers' },
    soap: { icon: ClipboardList, label: 'SOAP' },
  };

  return (
    <div className="fi-card-xl animate-in fade-in">
      <div className="flex items-center gap-2 mb-4">
        <Loader2 className="h-5 w-5 fi-text-info animate-spin" />
        <h3 className="fi-title">Procesamiento Backend FI</h3>
      </div>

      {/* Progress Bar with gradient */}
      <div className="mb-6">
        <div className="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
          <div
            className="med-progress-bar"
            style={{ width: `${workflowStatus.progress_pct}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-2">
          <p className="fi-subtitle">{workflowStatus.progress_pct}% completado</p>
          <p className="fi-text-xs-muted">Backend con VAD automático</p>
        </div>
      </div>

      {/* Stage Status Grid with Icons */}
      <div className="grid grid-cols-2 gap-3">
        {Object.entries(workflowStatus.stages).map(([stage, status]) => {
          const isActive = status === 'in_progress';
          const isComplete = status === 'completed';
          const isFailed = status === 'failed';
          const config = stageConfig[stage];
          const StageIcon = config?.icon;

          return (
            <div
              key={stage}
              className={
                isComplete ? 'fi-state-complete' :
                isActive ? 'fi-state-active' :
                isFailed ? 'fi-state-failed' :
                'fi-state-pending'
              }
            >
              <div className="fi-flex-between">
                <span className="fi-title-sm-medium flex items-center gap-1.5">
                  {StageIcon && <StageIcon className="w-4 h-4" strokeWidth={1.5} aria-hidden="true" />}
                  {config?.label || stage}
                </span>
                {isComplete && <Check className="h-4 w-4 fi-text-green" aria-hidden="true" />}
                {isActive && <Loader2 className="h-4 w-4 fi-text-info animate-spin" />}
                {isFailed && <X className="h-4 w-4 fi-text-error" aria-hidden="true" />}
              </div>
              <div className={`
                text-xs mt-1
                ${isComplete ? 'fi-text-green' : ''}
                ${isActive ? 'fi-text-info' : ''}
                ${isFailed ? 'fi-text-error' : ''}
                ${status === 'pending' ? 'text-slate-400' : ''}
              `}>
                {status === 'in_progress' ? 'Procesando...' : status}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
