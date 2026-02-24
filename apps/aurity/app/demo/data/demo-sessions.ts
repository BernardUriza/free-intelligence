import type { DemoSession } from '../types';

/** Generates 3 demo sessions (medical, legal, code) with realistic events. */
export function generateDemoSessions(): DemoSession[] {
  const now = Date.now();

  return [
    {
      id: 'demo_medical_001',
      type: 'medical',
      title: 'Consulta Pediátrica - Fiebre',
      description: 'Paciente de 4 años con fiebre de 38.5°C por 2 días',
      eventCount: 10,
      created_at: new Date(now - 3600000).toISOString(),
      events: [
        { id: 'ev_m_001', type: 'speech', speaker: 'Madre', content: 'Mi hija tiene fiebre desde hace dos días, llegó a 38.5 grados.', timestamp: 0 },
        { id: 'ev_m_002', type: 'speech', speaker: 'Doctor', content: '¿Ha tenido otros síntomas como tos, dolor de garganta o diarrea?', timestamp: 4000 },
        { id: 'ev_m_003', type: 'speech', speaker: 'Madre', content: 'Sí, ayer comenzó con un poco de tos y se queja de dolor de garganta.', timestamp: 8000 },
        { id: 'ev_m_004', type: 'speech', speaker: 'Doctor', content: 'Entiendo. ¿Ha estado en contacto con alguien enfermo recientemente?', timestamp: 12000 },
        { id: 'ev_m_005', type: 'speech', speaker: 'Madre', content: 'Sí, su hermano tuvo gripe la semana pasada.', timestamp: 16000 },
        { id: 'ev_m_006', type: 'diarization', content: 'Diarización completada: 2 hablantes identificados', timestamp: 18000, metadata: { speakers: 2, confidence: 0.94 } },
        { id: 'ev_m_007', type: 'vitals', content: 'T: 38.5°C, FR: 24/min, FC: 110/min', timestamp: 20000, metadata: { temp: 38.5, fr: 24, fc: 110 } },
        { id: 'ev_m_008', type: 'exam', content: 'Faringe eritematosa, sin exudado. Auscultación pulmonar sin ruidos anormales.', timestamp: 25000 },
        { id: 'ev_m_009', type: 'assessment', content: 'Infección viral de vías respiratorias superiores (probable gripe)', timestamp: 30000 },
        { id: 'ev_m_010', type: 'plan', content: 'Paracetamol 15mg/kg cada 6h PRN fiebre. Control en 48h si persiste.', timestamp: 35000 },
      ],
    },
    {
      id: 'demo_legal_002',
      type: 'legal',
      title: 'Consulta Legal - Contrato Laboral',
      description: 'Revisión de cláusulas de no competencia en contrato de trabajo',
      eventCount: 8,
      created_at: new Date(now - 7200000).toISOString(),
      events: [
        { id: 'ev_l_001', type: 'speech', speaker: 'Cliente', content: 'Me ofrecieron un nuevo trabajo pero mi contrato actual tiene una cláusula de no competencia.', timestamp: 0 },
        { id: 'ev_l_002', type: 'speech', speaker: 'Abogado', content: '¿Puede mostrarme el contrato? Necesito ver la redacción exacta de la cláusula.', timestamp: 5000 },
        { id: 'ev_l_003', type: 'document', content: 'Contrato de trabajo recibido - 12 páginas', timestamp: 8000, metadata: { pages: 12, format: 'pdf' } },
        { id: 'ev_l_004', type: 'analysis', content: 'Cláusula 15.3: Prohibición de trabajar en empresas competidoras por 2 años', timestamp: 15000 },
        { id: 'ev_l_005', type: 'speech', speaker: 'Abogado', content: 'La cláusula es muy amplia geográficamente. Esto podría ser impugnable.', timestamp: 20000 },
        { id: 'ev_l_006', type: 'research', content: 'Jurisprudencia: 3 casos similares en México (2023-2024)', timestamp: 25000, metadata: { cases: 3 } },
        { id: 'ev_l_007', type: 'recommendation', content: 'Se recomienda negociar reducción del período a 6 meses y limitación geográfica.', timestamp: 30000 },
        { id: 'ev_l_008', type: 'action', content: 'Carta de negociación preparada para envío', timestamp: 35000 },
      ],
    },
    {
      id: 'demo_code_003',
      type: 'code',
      title: 'Code Review - API Authentication',
      description: 'Review of JWT implementation and security patterns',
      eventCount: 12,
      created_at: new Date(now - 1800000).toISOString(),
      events: [
        { id: 'ev_c_001', type: 'context', content: 'Reviewing auth.ts - JWT token generation and validation', timestamp: 0 },
        { id: 'ev_c_002', type: 'file_read', content: 'src/auth/jwt.ts - 245 lines', timestamp: 2000, metadata: { lines: 245, path: 'src/auth/jwt.ts' } },
        { id: 'ev_c_003', type: 'issue', content: 'SECURITY: Token expiration set to 30 days - too long', timestamp: 5000, metadata: { severity: 'high' } },
        { id: 'ev_c_004', type: 'suggestion', content: 'Recommend 15 minute access tokens with refresh token pattern', timestamp: 8000 },
        { id: 'ev_c_005', type: 'file_read', content: 'src/middleware/auth.ts - 89 lines', timestamp: 10000, metadata: { lines: 89 } },
        { id: 'ev_c_006', type: 'issue', content: 'Missing rate limiting on login endpoint', timestamp: 12000, metadata: { severity: 'medium' } },
        { id: 'ev_c_007', type: 'code_change', content: 'Added rate limiter: 5 attempts per minute per IP', timestamp: 15000 },
        { id: 'ev_c_008', type: 'file_read', content: 'src/utils/crypto.ts - 56 lines', timestamp: 18000, metadata: { lines: 56 } },
        { id: 'ev_c_009', type: 'approval', content: 'Crypto utils using bcrypt with cost factor 12 - approved', timestamp: 20000 },
        { id: 'ev_c_010', type: 'test', content: 'Running auth test suite: 23 tests', timestamp: 22000, metadata: { total: 23 } },
        { id: 'ev_c_011', type: 'test_result', content: '23/23 tests passing', timestamp: 28000, metadata: { passed: 23, failed: 0 } },
        { id: 'ev_c_012', type: 'summary', content: 'Review complete: 2 issues found, 1 fixed, 1 pending team discussion', timestamp: 32000 },
      ],
    },
  ];
}
