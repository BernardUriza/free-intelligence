/**
 * ConversationCapture Types
 *
 * Shared interfaces for the medical conversation capture workflow.
 */

import type { TranscriptionData } from '@aurity-standalone/hooks/useTranscription';

export interface ConversationCaptureProps {
  onNext?: () => void;
  onTranscriptionComplete?: (data: TranscriptionData) => void;
  isRecording?: boolean;
  setIsRecording?: (recording: boolean) => void;
  onSessionCreated?: (sessionId: string) => void;
  sessionId?: string;
  readOnly?: boolean;
  patient?: { id: string; name: string; age: number };
  className?: string;
}

export interface WorkflowStatus {
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
  soap_note?: unknown;
  result_data?: unknown;
  error?: string;
}

export interface ChunkMetric {
  chunk_number: number;
  text: string;
  provider?: string;
  polling_attempts?: number;
  resolution_time_seconds?: number;
  retry_attempts?: number;
  confidence?: number;
  duration?: number;
}

export interface ChunkStatus {
  index: number;
  status: 'uploading' | 'pending' | 'completed' | 'failed' | 'processing' | 'unresolved';
  startTime: number;
  latency?: number;
  transcript?: string;
  provider?: string;
  resolution_time_seconds?: number;
  retry_attempts?: number;
  polling_attempts?: number;
  confidence?: number;
  duration?: number;
}
