// @ts-nocheck - Mock fixtures may have slightly different shapes for testing
import type { DiarizationSegment, MedicalOrder, SOAPNoteResponse, StreamChunkResponse } from '@aurity-standalone/api-client/medical-workflow';

export const sessionId = 'mock-session-001';

export const streamChunkResponse = (chunkNumber: number): StreamChunkResponse => ({
  chunk_number: chunkNumber,
  session_id: sessionId,
  transcript: `Transcription chunk ${chunkNumber}`,
  transcript_delta: chunkNumber % 2 === 0 ? undefined : `delta ${chunkNumber}`,
});

export const checkpointResponse = {
  checkpoint_at: new Date().toISOString(),
  chunks_concatenated: 12,
  full_audio_size: 1_024_000,
};

export const endSessionResponse = {
  success: true,
  session_id: sessionId,
  audio_path: `/storage/${sessionId}/full.wav`,
  chunks_count: 12,
  duration: 420,
};

export const diarizationJobId = 'dia-job-123';
export const diarizationSegments: DiarizationSegment[] = [
  { speaker: 'MEDICO', text: 'Buenos dias, cuentame.', start_time: 0, end_time: 4 },
  { speaker: 'PACIENTE', text: 'Tengo dolor leve de cabeza.', start_time: 4, end_time: 10 },
];

export const soapNote: SOAPNoteResponse = {
  soap_note: {
    subjective: {
      chief_complaint: 'Dolor de cabeza leve',
      history_of_present_illness: 'Desde hace 2 dias, sin fiebre.',
      medical_history: 'Sin antecedentes relevantes',
      review_of_systems: [],
    },
    objective: {
      vital_signs: {
        heart_rate: 72,
        blood_pressure: '120/80',
        respiratory_rate: 16,
        temperature_celsius: 36.5,
      },
      physical_exam: 'Normal, sin focalidad neurológica.',
    },
    assessment: {
      primary_diagnosis: 'Cefalea tensional',
      differential_diagnoses: ['Migraña leve'],
    },
    plan: {
      medications: ['Paracetamol 500mg c/8h PRN'],
      studies: ['Ninguno'],
      follow_up: 'Revisar en 1 semana si no mejora',
      treatment: 'Reposo, hidratación',
    },
  },
};

export const medicalOrders: MedicalOrder[] = [
  {
    id: 'order-1',
    type: 'medication',
    description: 'Paracetamol 500mg c/8h PRN',
    details: 'Tabletas',
    source: 'manual',
    created_at: new Date().toISOString(),
  },
  {
    id: 'order-2',
    type: 'lab',
    description: 'BH completa',
    source: 'manual',
    created_at: new Date().toISOString(),
  },
];

export const transcriptionSources = {
  webspeech_final: ['Hola, buenos dias'],
  transcription_per_chunks: [
    {
      chunk_number: 0,
      text: 'Inicio de la consulta',
      created_at: new Date().toISOString(),
    },
    {
      chunk_number: 1,
      text: 'Paciente refiere dolor',
      created_at: new Date().toISOString(),
    },
  ],
  full_transcription: 'Inicio de la consulta. Paciente refiere dolor.',
};

export const sessionMonitorText = `TASK SOAP_GENERATION ✅\nTASK TRANSCRIPTION ✅\nESTIMATED_SECONDS_REMAINING: 30`;

export const timelineSession = {
  session_id: sessionId,
  patient_name: 'Paciente Demo',
  start_time: new Date(Date.now() - 3_600_000).toISOString(),
  status: 'completed',
};

export const timelineEvents = [
  {
    id: 'evt-1',
    type: 'session_start',
    timestamp: new Date(Date.now() - 3_600_000).toISOString(),
    description: 'Sesion iniciada',
  },
  {
    id: 'evt-2',
    type: 'soap_created',
    timestamp: new Date(Date.now() - 3_300_000).toISOString(),
    description: 'Nota SOAP generada',
  },
];

export const kpiSummary = {
  sessions_today: 24,
  avg_duration_minutes: 18,
  active_users: 7,
  system_health: 'healthy',
};
