/**
 * Mock Backend for Development
 * 
 * Provides mock responses for all backend endpoints when developing
 * without a running backend server.
 * 
 * Usage:
 * ```typescript
 * import { mockBackend } from '@/lib/api/mock-backend';
 * 
 * // Enable mock mode
 * if (process.env.NEXT_PUBLIC_MOCK_BACKEND === 'true') {
 *   const response = await mockBackend.chat({ message: "Hello" });
 * }
 * ```
 * 
 * @module lib/api/mock-backend
 */

import type { ChatRequest, ChatResponse } from '@aurity-standalone/api-client/assistant';

/**
 * Mock chat response with realistic delay
 */
export async function mockChat(_request: ChatRequest): Promise<ChatResponse> {
  // Simulate network delay (500-1500ms)
  await sleep(500 + Math.random() * 1000);

  const mockResponses = [
    "Entendido. He registrado la información en la nota SOAP.",
    "Por supuesto, actualizaré el registro del paciente.",
    "He añadido esa observación al expediente clínico.",
    "Perfecto, quedó documentado en el sistema.",
    "Registrado. ¿Hay algo más que agregar a esta consulta?",
  ];

  return {
    message: mockResponses[Math.floor(Math.random() * mockResponses.length)],
    persona: 'general_assistant',
    voice: 'nova',
  };
}

/**
 * Mock sessions list
 */
export async function mockGetSessions(): Promise<any[]> {
  await sleep(300);

  return [
    {
      session_id: 'session_mock_001',
      patient_name: 'Paciente Demo 1',
      start_time: new Date(Date.now() - 3600000).toISOString(),
      status: 'completed',
    },
    {
      session_id: 'session_mock_002',
      patient_name: 'Paciente Demo 2',
      start_time: new Date(Date.now() - 7200000).toISOString(),
      status: 'completed',
    },
  ];
}

/**
 * Mock SOAP note
 */
export async function mockGetSOAP(sessionId: string): Promise<any> {
  await sleep(400);

  return {
    session_id: sessionId,
    subjective: "Paciente refiere dolor de cabeza leve desde hace 2 días.",
    objective: "TA: 120/80, FC: 72 lpm, Temp: 36.5°C. Paciente alerta y orientado.",
    assessment: "Probable cefalea tensional.",
    plan: "Prescribir paracetamol 500mg c/8h PRN. Seguimiento en 1 semana si persiste.",
  };
}

/**
 * Mock personas list
 */
export async function mockGetPersonas(): Promise<any> {
  await sleep(200);

  return {
    personas: [
      {
        id: 'general_assistant',
        name: 'Asistente General',
        description: 'Asistente médico general para consultas variadas',
        model: 'mock-model',
        temperature: 0.7,
      },
      {
        id: 'soap_editor',
        name: 'Editor SOAP',
        description: 'Especialista en notas clínicas formato SOAP',
        model: 'mock-model',
        temperature: 0.3,
      },
    ],
  };
}

/**
 * Mock KPIs data
 */
export async function mockGetKPIs(): Promise<any> {
  await sleep(250);

  return {
    sessions_today: Math.floor(Math.random() * 50) + 10,
    avg_duration_minutes: Math.floor(Math.random() * 30) + 15,
    active_users: Math.floor(Math.random() * 20) + 5,
    system_health: 'healthy',
  };
}

/**
 * Mock timeline data
 */
export async function mockGetTimeline(): Promise<any[]> {
  await sleep(350);

  const now = Date.now();
  return [
    {
      id: 'event_001',
      type: 'session_start',
      timestamp: new Date(now - 3600000).toISOString(),
      description: 'Consulta iniciada',
    },
    {
      id: 'event_002',
      type: 'soap_created',
      timestamp: new Date(now - 3000000).toISOString(),
      description: 'Nota SOAP generada',
    },
    {
      id: 'event_003',
      type: 'session_end',
      timestamp: new Date(now - 2400000).toISOString(),
      description: 'Consulta finalizada',
    },
  ];
}

/**
 * Mock health check
 */
export async function mockHealthCheck(): Promise<any> {
  await sleep(100);

  return {
    status: 'ok',
    version: 'mock-0.1.0',
    timestamp: new Date().toISOString(),
  };
}

/**
 * Centralized mock backend API
 */
export const mockBackend = {
  chat: mockChat,
  getSessions: mockGetSessions,
  getSOAP: mockGetSOAP,
  getPersonas: mockGetPersonas,
  getKPIs: mockGetKPIs,
  getTimeline: mockGetTimeline,
  health: mockHealthCheck,
};

/**
 * Check if mock backend is enabled
 */
export function isMockBackendEnabled(): boolean {
  return process.env.NEXT_PUBLIC_MOCK_BACKEND === 'true';
}

/**
 * Sleep utility for simulating network delay
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Example usage in API client:
 * 
 * ```typescript
 * import { isMockBackendEnabled, mockBackend } from '@/lib/api/mock-backend';
 * 
 * export async function fetchSessions() {
 *   if (isMockBackendEnabled()) {
 *     return mockBackend.getSessions();
 *   }
 *   
 *   // Real API call
 *   return api.get('/api/aurity/medical-ai/sessions');
 * }
 * ```
 */
