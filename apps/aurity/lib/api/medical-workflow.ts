/**
 * Medical Workflow API Service
 *
 * Centralized API for medical recording workflow:
 * - Audio streaming & chunks
 * - Diarization (speaker separation)
 * - SOAP note generation
 * - Session management
 *
 * Replaces hardcoded URLs scattered across ConversationCapture
 *
 * Author: Senior Frontend Dev
 * Created: 2025-11-15
 */

import { api, getBackendUrl } from './client';

// ============================================================================
// Types
// ============================================================================

export interface StreamChunkResponse {
  success?: boolean; // Legacy field
  chunk_number: number;
  session_id: string;
  status?: 'pending' | 'in_progress' | 'completed' | 'failed'; // Current backend format
  total_chunks?: number;
  processed_chunks?: number;
  audio_hash?: string;
  transcript?: string;
  job_id?: string;
}

export interface CheckpointResponse {
  session_id: string;
  checkpoint_at: string;
  chunks_concatenated: number;
  full_audio_size: number;
  message: string;
}

export interface DiarizationJobResponse {
  job_id: string;
  session_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;
}

export interface DiarizationStatusResponse {
  job_id: string;
  session_id: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;
  segment_count: number;
  transcription_sources: {
    webspeech_final?: unknown[];
    transcription_per_chunks?: string[];
    full_transcription?: string;
  } | null;
  error: string | null;
}

export interface SOAPGenerationResponse {
  job_id: string;
  session_id: string;
  status: 'dispatched' | 'pending' | 'in_progress' | 'completed' | 'failed';
  message?: string;
}

export interface SOAPNoteResponse {
  session_id: string;
  soap_note: {
    subjective: {
      chief_complaint: string;
      history_present_illness: string;
      past_medical_history: string;
    };
    objective: {
      vital_signs: string;
      physical_exam: string;
    };
    assessment: {
      primary_diagnosis: string;
      differential_diagnoses: string[];
    };
    plan: {
      treatment: string;
      follow_up: string;
      studies: string[];
    };
  };
  provider: string;
  completed_at: string;
  word_count: number;
}

export interface DiarizationSegment {
  speaker: string;
  text: string;
  start_time: number;
  end_time: number;
  confidence?: number;
  improved_text?: string;
}

export interface SOAPNote {
  subjective?: {
    chiefComplaint?: string;
    hpi?: string;
    pastMedicalHistory?: string[];
    allergies?: string[];
  };
  objective?: {
    vitalSigns?: string;
    physicalExam?: string;
  };
  assessment?: {
    primaryDiagnosis?: string;
    differentialDiagnoses?: string[];
  };
  plan?: {
    medications?: Array<{
      name: string;
      dose: string;
      frequency: string;
      duration?: string;
      route?: string;
    }>;
    studies?: string[];
    followUp?: string;
    treatment?: string;
  };
}

export interface SOAPResponse {
  session_id: string;
  soap: SOAPNote;
}

export interface MedicalOrder {
  id: string;
  type: 'medication' | 'lab' | 'imaging' | 'followup';
  description: string;
  details?: string;
  created_at?: string;
  updated_at?: string;
  source?: 'soap' | 'manual';
}

export interface OrdersResponse {
  session_id: string;
  orders: MedicalOrder[];
  order_count: number;
}

export interface DiarizationSegmentsResponse {
  session_id: string;
  segments: DiarizationSegment[];
  segment_count: number;
  provider: string;
  completed_at: string;
}

export interface EndSessionResponse {
  success: boolean;
  session_id: string;
  audio_path: string;
  chunks_count: number;
  duration: number;
}

// ============================================================================
// Medical Workflow API
// ============================================================================

export const medicalWorkflowApi = {
  /**
   * Upload audio chunk for streaming transcription
   */
  uploadChunk: async (
    sessionId: string,
    chunkNumber: number,
    audioBlob: Blob,
    options?: {
      timestampStart?: number;
      timestampEnd?: number;
      filename?: string;
      patientInfo?: {
        patient_name?: string;
        patient_age?: string;
        patient_id?: string;
        chief_complaint?: string;
      };
    }
  ): Promise<StreamChunkResponse> => {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('chunk_number', chunkNumber.toString());
    formData.append('mime', audioBlob.type || '');

    // Include patient info in first chunk only
    if (chunkNumber === 0 && options?.patientInfo) {
      if (options.patientInfo.patient_name) {
        formData.append('patient_name', options.patientInfo.patient_name);
      }
      if (options.patientInfo.patient_age) {
        formData.append('patient_age', options.patientInfo.patient_age);
      }
      if (options.patientInfo.patient_id) {
        formData.append('patient_id', options.patientInfo.patient_id);
      }
      if (options.patientInfo.chief_complaint) {
        formData.append('chief_complaint', options.patientInfo.chief_complaint);
      }
    }

    const filename = options?.filename || `chunk_${chunkNumber.toString().padStart(3, '0')}.webm`;
    formData.append('audio', audioBlob, filename);

    if (options?.timestampStart !== undefined) {
      formData.append('timestamp_start', options.timestampStart.toString());
    }
    if (options?.timestampEnd !== undefined) {
      formData.append('timestamp_end', options.timestampEnd.toString());
    }

    return api.upload<StreamChunkResponse>(
      '/api/aurity/stream',
      formData
    );
  },

  /**
   * Create checkpoint (concatenate audio on pause)
   */
  createCheckpoint: async (
    sessionId: string,
    lastChunkIdx?: number
  ): Promise<CheckpointResponse> => {
    return api.post<CheckpointResponse>(
      `/api/aurity/medical-ai/sessions/${sessionId}/checkpoint`,
      lastChunkIdx !== undefined ? { last_chunk_idx: lastChunkIdx } : undefined
    );
  },

  /**
   * End session and save full audio
   */
  endSession: async (
    sessionId: string,
    fullAudioBlob: Blob,
    webSpeechTranscripts?: string[]
  ): Promise<EndSessionResponse> => {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('full_audio', fullAudioBlob, 'session.webm');

    // Include webspeech transcripts for Triple Vision diarization
    if (webSpeechTranscripts && webSpeechTranscripts.length > 0) {
      formData.append('webspeech_final', JSON.stringify(webSpeechTranscripts));
    }

    return api.upload<EndSessionResponse>(
      '/api/aurity/end-session',
      formData
    );
  },

  /**
   * Start diarization (speaker separation)
   */
  startDiarization: async (sessionId: string): Promise<DiarizationJobResponse> => {
    return api.post<DiarizationJobResponse>(
      `/api/aurity/medical-ai/sessions/${sessionId}/diarization`
    );
  },

  /**
   * Get diarization job status (for polling)
   */
  getDiarizationStatus: async (jobId: string): Promise<DiarizationStatusResponse> => {
    return api.get<DiarizationStatusResponse>(
      `/api/aurity/medical-ai/diarization/jobs/${jobId}`
    );
  },

  /**
   * Start SOAP note generation (Phase 4)
   */
  startSOAPGeneration: async (sessionId: string): Promise<SOAPGenerationResponse> => {
    return api.post<SOAPGenerationResponse>(
      `/api/aurity/medical-ai/sessions/${sessionId}/soap`
    );
  },

  /**
   * Get SOAP note (after completion)
   * Use getSessionMonitor() to poll for SOAP generation status
   */
  getSOAPNote: async (sessionId: string): Promise<SOAPNoteResponse> => {
    return api.get<SOAPNoteResponse>(
      `/api/aurity/medical-ai/sessions/${sessionId}/soap`
    );
  },

  /**
   * Get diarization segments (after completion)
   */
  getDiarizationSegments: async (sessionId: string): Promise<DiarizationSegmentsResponse> => {
    return api.get<DiarizationSegmentsResponse>(
      `/api/aurity/medical-ai/sessions/${sessionId}/diarization/segments`
    );
  },

  /**
   * Get session monitor (real-time progress with ASCII art)
   */
  getSessionMonitor: async (sessionId: string): Promise<string> => {
    // Use api client instead of hardcoded fetch
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001'}/api/aurity/medical-ai/sessions/${sessionId}/monitor`,
      {
        method: 'GET',
        headers: { 'Accept': 'text/plain' },
      }
    );

    if (!response.ok) {
      throw new Error(`Monitor API error: ${response.status}`);
    }

    return response.text();
  },

  /**
   * Update diarization segment text (edit transcription)
   */
  updateSegmentText: async (
    sessionId: string,
    segmentIndex: number,
    newText: string
  ): Promise<DiarizationSegment> => {
    const response = await api.patch<{ segment: DiarizationSegment }>(
      `/api/aurity/medical-ai/sessions/${sessionId}/diarization/segments/${segmentIndex}`,
      { text: newText }
    );
    return response.segment;
  },

  // ============================================================================
  // SOAP CRUD
  // ============================================================================

  /**
   * Get SOAP note for a session
   */
  getSOAP: async (sessionId: string): Promise<SOAPNote> => {
    const response = await api.get<SOAPResponse>(
      `/api/aurity/medical-ai/sessions/${sessionId}/soap`
    );
    return response.soap;
  },

  /**
   * Update SOAP note (triggers auto-creation of orders)
   */
  updateSOAP: async (sessionId: string, soap: SOAPNote): Promise<{ orders_created: number }> => {
    return api.put<{ success: boolean; orders_created: number }>(
      `/api/aurity/medical-ai/sessions/${sessionId}/soap`,
      { soap }
    );
  },

  // ============================================================================
  // ORDERS CRUD
  // ============================================================================

  /**
   * Get all medical orders for a session
   */
  getOrders: async (sessionId: string): Promise<MedicalOrder[]> => {
    const response = await api.get<OrdersResponse>(
      `/api/aurity/medical-ai/sessions/${sessionId}/orders`
    );
    return response.orders;
  },

  /**
   * Create a new medical order
   */
  createOrder: async (
    sessionId: string,
    order: {
      type: MedicalOrder['type'];
      description: string;
      details?: string;
    }
  ): Promise<string> => {
    const response = await api.post<{ success: boolean; order_id: string }>(
      `/api/aurity/medical-ai/sessions/${sessionId}/orders`,
      order
    );
    return response.order_id;
  },

  /**
   * Update an existing order
   */
  updateOrder: async (
    sessionId: string,
    orderId: string,
    order: {
      type: MedicalOrder['type'];
      description: string;
      details?: string;
    }
  ): Promise<void> => {
    await api.put(
      `/api/aurity/medical-ai/sessions/${sessionId}/orders/${orderId}`,
      order
    );
  },

  /**
   * Delete an order
   */
  deleteOrder: async (sessionId: string, orderId: string): Promise<void> => {
    await api.delete(
      `/api/aurity/medical-ai/sessions/${sessionId}/orders/${orderId}`
    );
  },

  /**
   * Get all transcription chunks for a session
   */
  getTranscriptionChunks: async (sessionId: string): Promise<{
    session_id: string;
    chunks: Array<{
      chunk_number: number;
      transcript: string;
      duration: number;
      created_at: string;
      status: string;
    }>;
    total_duration: number;
    total_chunks: number;
  }> => {
    return api.get(
      `/api/aurity/medical-ai/sessions/${sessionId}/chunks`
    );
  },

  /**
   * Get all 3 transcription sources for a saved session (Triple Vision)
   */
  getTranscriptionSources: async (sessionId: string): Promise<{
    webspeech_final: string[];
    transcription_per_chunks: Array<{
      chunk_number: number;
      transcript: string;
      timestamp_start: number;
      timestamp_end: number;
      duration: number;
      provider: string;
      confidence: number;
      resolution_time_seconds: number;
      retry_attempts: number;
      polling_attempts: number;
    }>;
    full_transcription: string;
  }> => {
    return api.get(
      `/api/aurity/medical-ai/sessions/${sessionId}/transcription-sources`
    );
  },
};
