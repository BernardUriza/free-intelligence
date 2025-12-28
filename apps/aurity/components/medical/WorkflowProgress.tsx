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

import { Loader2 } from 'lucide-react';

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
  const stageLabels: Record<string, string> = {
    upload: '📤 Upload',
    transcribe: '🎤 Whisper',
    diarize: '👥 Speakers',
    soap: '📋 SOAP'
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
            className="h-3 rounded-full transition-all duration-500 ease-out bg-gradient-to-r from-emerald-500 to-cyan-500"
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
                <span className="fi-title-sm-medium">
                  {stageLabels[stage] || stage}
                </span>
                {isComplete && <span className="fi-text-green">✓</span>}
                {isActive && <Loader2 className="h-4 w-4 fi-text-info animate-spin" />}
                {isFailed && <span className="fi-text-error">✗</span>}
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
