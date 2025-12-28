/**
 * Session types for new HDF5 architecture with 3 transcription sources
 *
 * Author: Bernard Uriza Orozco
 * Created: 2025-11-14
 */

export enum SessionStatus {
  ACTIVE = "active",
  FINALIZED = "finalized",
  DIARIZED = "diarized",
  REVIEWED = "reviewed",
  COMPLETED = "completed"
}

export interface EncryptionMetadata {
  algorithm: string;
  key_id: string;
  iv: string;
  encrypted_at: string;
  encrypted_by?: string;
}

export interface ChunkTranscript {
  chunk_number: number;
  text: string;
  latency_ms?: number;
}

export interface TranscriptionSources {
  webspeech_final: string[];
  transcription_per_chunks: ChunkTranscript[];
  full_transcription: string;
}

export interface DiarizationMetadata {
  diarization_completed_at?: string;
  diarization_segment_count?: number;
  diarization_model?: string;
}

export interface SessionMetadata {
  session_id: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  recording_duration: number;
  total_chunks: number;
  encryption_metadata?: EncryptionMetadata;
  transcription_sources?: TranscriptionSources;
  diarization_job_id?: string;
  finalized_at?: string;
  diarized_at?: string;
  // Diarization metadata (added by diarization task)
  diarization_completed_at?: string;
  diarization_segment_count?: number;
  diarization_model?: string;
}

export interface Session {
  session_id: string;
  metadata: SessionMetadata;
}

export interface SessionDetailResponse extends Session {
  // Additional fields that might be added by the API
}

export interface SessionsListResponse {
  sessions: Session[];
  total: number;
  page?: number;
  limit?: number;
}
