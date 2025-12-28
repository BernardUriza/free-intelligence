/**
 * Simulation Data - Phase 6 (FI-ONBOARD-007)
 *
 * Mock data for consultation simulation:
 * - Audio chunks (fake binary data)
 * - Transcription results
 * - Diarization output
 * - SOAP notes
 */

export interface AudioChunkSimulation {
  chunk_number: number;
  size_kb: number;
  duration_seconds: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
}

export interface TranscriptionResult {
  chunk_number: number;
  text: string;
  confidence: number;
  duration_ms: number;
}

export interface DiarizationSegment {
  speaker: 'Médico' | 'Paciente';
  start_time: string;
  end_time: string;
  text: string;
}

export interface SOAPNotes {
  subjetivo: string;
  objetivo: string;
  analisis: string;
  plan: string;
  completeness: number;
}

/**
 * Simulated audio chunks (6 chunks for demo)
 */
export const SIMULATED_CHUNKS: AudioChunkSimulation[] = [
  { chunk_number: 0, size_kb: 125, duration_seconds: 28, status: 'pending' },
  { chunk_number: 1, size_kb: 132, duration_seconds: 30, status: 'pending' },
  { chunk_number: 2, size_kb: 118, duration_seconds: 26, status: 'pending' },
  { chunk_number: 3, size_kb: 140, duration_seconds: 32, status: 'pending' },
  { chunk_number: 4, size_kb: 128, duration_seconds: 29, status: 'pending' },
  { chunk_number: 5, size_kb: 135, duration_seconds: 31, status: 'pending' },
];

/**
 * Simulated transcription results
 */
export const SIMULATED_TRANSCRIPTIONS: TranscriptionResult[] = [
  {
    chunk_number: 0,
    text: 'Médico: Buenos días, ¿cómo se encuentra hoy? Paciente: Buenos días doctor, la verdad me he sentido un poco cansado últimamente, con algunos dolores de cabeza.',
    confidence: 0.94,
    duration_ms: 2100,
  },
  {
    chunk_number: 1,
    text: 'Médico: Entiendo. ¿Desde cuándo empezó con estos síntomas? Paciente: Hace aproximadamente dos semanas, al principio pensé que era estrés del trabajo.',
    confidence: 0.91,
    duration_ms: 2300,
  },
  {
    chunk_number: 2,
    text: 'Médico: ¿Ha notado si los dolores de cabeza tienen algún patrón? ¿Intensidad en cierto momento del día? Paciente: Sí, generalmente son más fuertes por la tarde, después de las 3 o 4 PM.',
    confidence: 0.96,
    duration_ms: 1900,
  },
  {
    chunk_number: 3,
    text: 'Médico: Voy a tomarle la presión arterial. Relájese por favor. Paciente: Claro, doctor. Médico: 135 sobre 85... está un poco elevada. ¿Ha tenido antecedentes de presión alta?',
    confidence: 0.89,
    duration_ms: 2400,
  },
  {
    chunk_number: 4,
    text: 'Paciente: Mi padre tuvo hipertensión, pero yo nunca había tenido problemas. Médico: Es importante que empecemos a monitorear esto de cerca. Le voy a recetar un medicamento y necesito que lleve un registro diario de su presión.',
    confidence: 0.93,
    duration_ms: 2200,
  },
  {
    chunk_number: 5,
    text: 'Médico: También le recomiendo reducir el consumo de sal y hacer ejercicio moderado al menos 30 minutos al día. Paciente: Entendido doctor, empezaré mañana mismo. Médico: Perfecto, nos vemos en dos semanas para seguimiento.',
    confidence: 0.95,
    duration_ms: 2000,
  },
];

/**
 * Simulated diarization output
 */
export const SIMULATED_DIARIZATION: DiarizationSegment[] = [
  {
    speaker: 'Médico',
    start_time: '00:00',
    end_time: '00:05',
    text: 'Buenos días, ¿cómo se encuentra hoy?',
  },
  {
    speaker: 'Paciente',
    start_time: '00:05',
    end_time: '00:15',
    text: 'Buenos días doctor, la verdad me he sentido un poco cansado últimamente, con algunos dolores de cabeza.',
  },
  {
    speaker: 'Médico',
    start_time: '00:15',
    end_time: '00:22',
    text: 'Entiendo. ¿Desde cuándo empezó con estos síntomas?',
  },
  {
    speaker: 'Paciente',
    start_time: '00:22',
    end_time: '00:30',
    text: 'Hace aproximadamente dos semanas, al principio pensé que era estrés del trabajo.',
  },
  {
    speaker: 'Médico',
    start_time: '00:30',
    end_time: '00:40',
    text: '¿Ha notado si los dolores de cabeza tienen algún patrón? ¿Intensidad en cierto momento del día?',
  },
  {
    speaker: 'Paciente',
    start_time: '00:40',
    end_time: '00:50',
    text: 'Sí, generalmente son más fuertes por la tarde, después de las 3 o 4 PM.',
  },
  {
    speaker: 'Médico',
    start_time: '00:50',
    end_time: '01:00',
    text: 'Voy a tomarle la presión arterial. Relájese por favor.',
  },
  {
    speaker: 'Paciente',
    start_time: '01:00',
    end_time: '01:02',
    text: 'Claro, doctor.',
  },
  {
    speaker: 'Médico',
    start_time: '01:02',
    end_time: '01:15',
    text: '135 sobre 85... está un poco elevada. ¿Ha tenido antecedentes de presión alta?',
  },
  {
    speaker: 'Paciente',
    start_time: '01:15',
    end_time: '01:25',
    text: 'Mi padre tuvo hipertensión, pero yo nunca había tenido problemas.',
  },
  {
    speaker: 'Médico',
    start_time: '01:25',
    end_time: '01:40',
    text: 'Es importante que empecemos a monitorear esto de cerca. Le voy a recetar un medicamento y necesito que lleve un registro diario de su presión.',
  },
  {
    speaker: 'Médico',
    start_time: '01:40',
    end_time: '01:55',
    text: 'También le recomiendo reducir el consumo de sal y hacer ejercicio moderado al menos 30 minutos al día.',
  },
  {
    speaker: 'Paciente',
    start_time: '01:55',
    end_time: '02:00',
    text: 'Entendido doctor, empezaré mañana mismo.',
  },
  {
    speaker: 'Médico',
    start_time: '02:00',
    end_time: '02:05',
    text: 'Perfecto, nos vemos en dos semanas para seguimiento.',
  },
];

/**
 * Simulated SOAP notes
 */
export const SIMULATED_SOAP: SOAPNotes = {
  subjetivo: `**Motivo de consulta:** Paciente refiere cansancio reciente y dolores de cabeza.

**Historia de enfermedad actual:**
- Inicio de síntomas: 2 semanas atrás
- Síntomas principales: Cansancio generalizado, cefaleas
- Patrón temporal: Dolores de cabeza más intensos por la tarde (3-4 PM)
- Interpretación inicial del paciente: Atribuyó síntomas a estrés laboral

**Antecedentes familiares:**
- Padre con historial de hipertensión arterial
- Paciente sin antecedentes previos de presión arterial elevada`,

  objetivo: `**Signos vitales:**
- Presión arterial: 135/85 mmHg (elevada)
- Estado general: Consciente, orientado, cooperador

**Exploración física:**
- Toma de presión arterial realizada con paciente en reposo
- No se reportan otros hallazgos físicos en la transcripción`,

  analisis: `**Impresión diagnóstica:**
- Pre-hipertensión / Hipertensión arterial grado 1
- Cefalea tensional probable (asociada a elevación de presión arterial)

**Factores de riesgo identificados:**
- Antecedente familiar de hipertensión (padre)
- Estrés laboral referido
- Patrón temporal de cefaleas (vespertino) sugiere relación con fatiga/tensión

**Diagnóstico diferencial:**
- Hipertensión arterial primaria
- Cefalea por tensión muscular
- Síndrome de estrés crónico`,

  plan: `**Tratamiento farmacológico:**
- Inicio de antihipertensivo (medicamento específico no mencionado en transcripción)

**Monitoreo:**
- Registro diario de presión arterial en casa
- Control en 2 semanas para evaluar respuesta al tratamiento

**Modificaciones de estilo de vida:**
- Reducción de consumo de sal en dieta
- Ejercicio moderado: mínimo 30 minutos diarios
- Inicio inmediato recomendado (paciente acepta comenzar al día siguiente)

**Seguimiento:**
- Cita programada en 2 semanas
- Objetivo: Evaluar respuesta a medicamento y ajuste de dosis si necesario`,

  completeness: 92,
};

/**
 * Progress messages for simulation
 */
export const PROGRESS_MESSAGES = {
  upload: [
    'Uploading chunk 1/6... (125 KB)',
    'Uploading chunk 2/6... (132 KB)',
    'Uploading chunk 3/6... (118 KB)',
    'Uploading chunk 4/6... (140 KB)',
    'Uploading chunk 5/6... (128 KB)',
    'Uploading chunk 6/6... (135 KB)',
  ],
  transcription: [
    'Transcribing chunk 1/6... (Deepgram)',
    'Transcribing chunk 2/6... (Azure Whisper)',
    'Transcribing chunk 3/6... (Deepgram)',
    'Transcribing chunk 4/6... (Deepgram)',
    'Transcribing chunk 5/6... (Azure Whisper)',
    'Transcribing chunk 6/6... (Deepgram)',
  ],
  diarization: 'Analyzing speaker patterns... (Azure GPT-4)',
  soap: 'Generating SOAP notes from conversation... (Claude Sonnet 4.5)',
};

/**
 * Simulate latency for operations (ms)
 */
export const LATENCY = {
  upload_per_chunk: 800,      // 0.8s per chunk upload
  transcription_per_chunk: 1200, // 1.2s per chunk transcription
  diarization_total: 3000,    // 3s for full diarization
  soap_generation: 4000,      // 4s for SOAP generation
  checkpoint: 1500,           // 1.5s for checkpoint concatenation
};

/**
 * ASCII Art for progress monitor
 */
export const ASCII_ART = {
  chunk_success: '█',
  chunk_pending: '░',
  chunk_in_progress: '▓',
  checkpoint: '║',
  separator: '─',
};
