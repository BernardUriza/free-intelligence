/**
 * API Route Prefixes - Single Source of Truth
 *
 * All API path prefixes live here. When the backend restructures routes,
 * change them in ONE place instead of 50+ hardcoded strings.
 *
 * Usage:
 *   import { ROUTES } from './routes';
 *   const API_BASE = ROUTES.clinics;
 *
 * Created: 2026-02-07
 * Card: FI-API-REFAC-001
 */

const API = '/api';
const API_AURITY = `${API}/aurity`;
const API_INTERNAL = '/internal';

export const ROUTES = {
  // Clinic domain
  clinics: `${API_AURITY}/clinic/clinics`,
  clinicMedia: `${API_AURITY}/clinic/clinic-media`,
  tvContent: `${API_AURITY}/clinic/tv-content`,
  clinicUsers: `${API_AURITY}/clinic/users/me`,
  waitingRoom: `${API_AURITY}/clinic/waiting-room`,
  widgetConfig: `${API_AURITY}/clinic/widget-config`,

  // AI
  assistant: `${API_AURITY}/assistant`,
  assistantHistory: `${API_AURITY}/assistant/history`,
  medicalAi: `${API_AURITY}/medical-ai`,

  // Core
  timeline: `${API_AURITY}/timeline`,
  sessions: `${API}/sessions`,
  auritySessions: `${API_AURITY}/sessions`,
  consult: `${API_AURITY}/consult`,
  prescriptions: `${API_AURITY}/prescriptions`,
  knowledgeBase: `${API_AURITY}/knowledge-base/documents`,
  system: `${API_AURITY}/system`,
  kpis: `${API_AURITY}/kpis`,
  health: `${API_AURITY}/health`,
  healthRoot: `${API}/health`,
  stream: `${API_AURITY}/transcription/stream`,
  endSession: `${API_AURITY}/transcription/end-session`,
  jobs: `${API_AURITY}/transcription/jobs`,
  tts: `${API}/tts`,
  workflowEvents: `${API}/workflows/events`,

  // Admin
  adminSystem: `${API}/admin/system`,
  adminLlmModels: `${API}/admin/llm-models`,
  adminPersonas: `${API}/admin/personas`,
  adminCatalog: `${API}/admin/catalog`,
  adminLicenses: `${API}/admin/licenses`,

  // Internal
  internalAdmin: `${API_INTERNAL}/admin`,
  internalDiarization: `${API_INTERNAL}/diarization`,
  internalTranscribe: `${API_INTERNAL}/transcribe`,

  // Aurity domain
  patients: `${API_AURITY}/patients`,
  checkin: `${API_AURITY}/checkin`,

  // Internal
  audit: `${API_INTERNAL}/audit`,
  exports: `${API_INTERNAL}/exports`,
  version: `${API}/version`,
  policy: `${API}/policy`,
  auth: `${API}/auth`,
  observability: `${API}/observability`,
} as const;
