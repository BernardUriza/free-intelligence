import type { ChatResponse, HistorySearchResponse } from '@aurity-standalone/api-client/assistant';

export const assistantGreeting: ChatResponse = {
  message: '¡Hola! Soy tu asistente clínico. ¿En qué puedo ayudarte hoy?',
  persona: 'general_assistant',
  voice: 'nova',
};

export const assistantChat: ChatResponse = {
  message: 'He registrado la indicación en la nota SOAP y generado las órdenes sugeridas.',
  persona: 'general_assistant',
  voice: 'nova',
  emotional_analysis: {
    state: 'calm',
    confidence: 0.82,
    suggested_tone: 'concise',
    reason: 'Clinical context with clear request',
  },
  thinking: 'Analizo la solicitud, reviso la nota y propongo órdenes.',
};

export const historySearchResponse: HistorySearchResponse = {
  results: [
    {
      session_id: 'mock-session-001',
      timestamp: new Date(Date.now() - 86_400_000).toISOString(),
      query: 'cefalea tensional',
      response: 'Se sugirió paracetamol y seguimiento en 1 semana.',
      relevance_score: 0.91,
    },
  ],
  total: 1,
  total_interactions: 1,
};
