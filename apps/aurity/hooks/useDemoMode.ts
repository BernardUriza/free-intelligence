/**
 * useDemoMode Hook
 *
 * Gestiona el modo demo con datos simulados:
 * - Detectar si está en modo demo
 * - Retornar datos mock para todas las fases del workflow
 * - Skip de llamadas API reales
 * - Simulación de delays realistas
 *
 * Extraído de ConversationCapture para reducir complejidad (P2 Refactoring)
 *
 * Created: 2025-01-XX
 * Author: Claude Code (P2 Architectural Refactoring)
 */

import { useState, useCallback } from 'react';

export interface DemoConsultation {
  sessionId: string;
  patientName: string;
  chiefComplaint: string;
  transcripts: string[];
  diarizationSegments: Array<{
    speaker: string;
    text: string;
    start_time: number;
    end_time: number;
  }>;
  soapNote?: {
    subjective: string;
    objective: string;
    assessment: string;
    plan: string;
  };
}

export interface DemoModeState {
  // State
  isDemoMode: boolean;
  currentDemo: DemoConsultation | null;

  // Actions
  enableDemoMode: (demo: DemoConsultation) => void;
  disableDemoMode: () => void;
  loadDemoConsultation: (consultationId: string) => Promise<void>;

  // Data Generators
  getMockTranscript: () => string;
  getMockDiarizationSegments: () => any[];
  getMockSOAPNote: () => any;

  // Helpers
  simulateDelay: (min: number, max: number) => Promise<void>;
  shouldSkipAPI: () => boolean;
}

const DEMO_CONSULTATIONS: Record<string, DemoConsultation> = {
  pediatric_fever: {
    sessionId: 'demo_pediatric_fever_001',
    patientName: 'Sofía García, 4 años',
    chiefComplaint: 'Fiebre de 38.5°C por 2 días',
    transcripts: [
      'Madre: Mi hija tiene fiebre desde hace dos días, llegó a 38.5 grados.',
      'Doctor: ¿Ha tenido otros síntomas como tos, dolor de garganta o diarrea?',
      'Madre: Sí, ayer comenzó con un poco de tos y se queja de dolor de garganta.',
      'Doctor: Entiendo. ¿Ha estado en contacto con alguien enfermo recientemente?',
      'Madre: Sí, su hermano tuvo gripe la semana pasada.',
    ],
    diarizationSegments: [
      { speaker: 'Madre', text: 'Mi hija tiene fiebre desde hace dos días, llegó a 38.5 grados.', start_time: 0, end_time: 4 },
      { speaker: 'Doctor', text: '¿Ha tenido otros síntomas como tos, dolor de garganta o diarrea?', start_time: 4, end_time: 8 },
      { speaker: 'Madre', text: 'Sí, ayer comenzó con un poco de tos y se queja de dolor de garganta.', start_time: 8, end_time: 12 },
      { speaker: 'Doctor', text: 'Entiendo. ¿Ha estado en contacto con alguien enfermo recientemente?', start_time: 12, end_time: 16 },
      { speaker: 'Madre', text: 'Sí, su hermano tuvo gripe la semana pasada.', start_time: 16, end_time: 19 },
    ],
    soapNote: {
      subjective: 'Paciente femenina de 4 años presenta fiebre de 38.5°C por 2 días, tos desde ayer, y dolor de garganta. Contacto reciente con hermano con gripe.',
      objective: 'T: 38.5°C, FR: 24/min, FC: 110/min. Faringe eritematosa, sin exudado. Auscultación pulmonar sin ruidos anormales.',
      assessment: 'Infección viral de vías respiratorias superiores (probable gripe).',
      plan: 'Paracetamol 15mg/kg cada 6h PRN fiebre. Abundantes líquidos. Control en 48h si persiste fiebre o empeoran síntomas.',
    },
  },
  hypertension_control: {
    sessionId: 'demo_hypertension_control_002',
    patientName: 'Roberto Sánchez, 58 años',
    chiefComplaint: 'Control de hipertensión arterial',
    transcripts: [
      'Paciente: Vengo por mi control de presión, doctor.',
      'Doctor: Perfecto. ¿Cómo se ha sentido? ¿Ha estado tomando sus medicamentos?',
      'Paciente: Sí, todos los días como me indicó. Me he sentido bien.',
      'Doctor: Excelente. ¿Ha medido su presión en casa?',
      'Paciente: Sí, he estado entre 130/80 y 135/85 en las mañanas.',
    ],
    diarizationSegments: [
      { speaker: 'Paciente', text: 'Vengo por mi control de presión, doctor.', start_time: 0, end_time: 3 },
      { speaker: 'Doctor', text: 'Perfecto. ¿Cómo se ha sentido? ¿Ha estado tomando sus medicamentos?', start_time: 3, end_time: 7 },
      { speaker: 'Paciente', text: 'Sí, todos los días como me indicó. Me he sentido bien.', start_time: 7, end_time: 11 },
      { speaker: 'Doctor', text: 'Excelente. ¿Ha medido su presión en casa?', start_time: 11, end_time: 14 },
      { speaker: 'Paciente', text: 'Sí, he estado entre 130/80 y 135/85 en las mañanas.', start_time: 14, end_time: 18 },
    ],
    soapNote: {
      subjective: 'Paciente masculino de 58 años con antecedente de HTA en control. Refiere apego a tratamiento y presiones en casa 130-135/80-85 mmHg.',
      objective: 'TA: 132/84 mmHg, FC: 72/min. Peso: 78kg (estable). Buena hidratación, sin edema.',
      assessment: 'Hipertensión arterial controlada con tratamiento actual.',
      plan: 'Continuar con Losartán 50mg/día. Control en 3 meses. Énfasis en dieta hiposódica y ejercicio regular.',
    },
  },
};

export function useDemoMode(): DemoModeState {
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [currentDemo, setCurrentDemo] = useState<DemoConsultation | null>(null);

  // Enable demo mode
  const enableDemoMode = useCallback((demo: DemoConsultation) => {
    setIsDemoMode(true);
    setCurrentDemo(demo);
    console.log('[Demo Mode] Enabled with:', demo.sessionId);
  }, []);

  // Disable demo mode
  const disableDemoMode = useCallback(() => {
    setIsDemoMode(false);
    setCurrentDemo(null);
    console.log('[Demo Mode] Disabled');
  }, []);

  // Simulate realistic delay
  const simulateDelay = useCallback((min: number, max: number): Promise<void> => {
    const delay = Math.random() * (max - min) + min;
    return new Promise((resolve) => setTimeout(resolve, delay));
  }, []);

  // Load demo consultation
  const loadDemoConsultation = useCallback(async (consultationId: string) => {
    const demo = DEMO_CONSULTATIONS[consultationId];
    if (demo) {
      await simulateDelay(500, 1000);
      enableDemoMode(demo);
    } else {
      console.warn(`[Demo Mode] Consultation ${consultationId} not found`);
    }
  }, [simulateDelay, enableDemoMode]);

  // Get mock transcript
  const getMockTranscript = useCallback((): string => {
    if (!currentDemo) return '';
    return currentDemo.transcripts.join('\n');
  }, [currentDemo]);

  // Get mock diarization segments
  const getMockDiarizationSegments = useCallback((): any[] => {
    if (!currentDemo) return [];
    return currentDemo.diarizationSegments;
  }, [currentDemo]);

  // Get mock SOAP note
  const getMockSOAPNote = useCallback((): any => {
    if (!currentDemo) return null;
    return currentDemo.soapNote;
  }, [currentDemo]);

  // Should skip API call
  const shouldSkipAPI = useCallback((): boolean => {
    return isDemoMode;
  }, [isDemoMode]);

  return {
    // State
    isDemoMode,
    currentDemo,

    // Actions
    enableDemoMode,
    disableDemoMode,
    loadDemoConsultation,

    // Data Generators
    getMockTranscript,
    getMockDiarizationSegments,
    getMockSOAPNote,

    // Helpers
    simulateDelay,
    shouldSkipAPI,
  };
}

// Export demo consultations for external use
export { DEMO_CONSULTATIONS };
