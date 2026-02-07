/**
 * @aurity-standalone/api-client
 *
 * Type-safe HTTP client for Aurity backend API.
 *
 * CONSOLIDATION: This package now re-exports from @/lib/api/ to eliminate
 * code duplication. The source of truth is lib/api/client.ts which uses
 * deployment.ts for proper backend URL resolution (Tauri/Cloud/Desktop).
 *
 * @packageDocumentation
 */

// Core client utilities - re-export from lib/api
export {
  api,
  apiRequest,
  apiUpload,
  APIError,
  getBackendUrl,
} from '../../../lib/api/client';

// API modules - re-export from lib/api
export * from '../../../lib/api/assistant';
export * from '../../../lib/api/personas';
export * from '../../../lib/api/llm-models';
export * from '../../../lib/api/knowledge';
export * from '../../../lib/api/checkin';
export * from '../../../lib/api/chat-history';
export * from '../../../lib/api/timeline';
export * from '../../../lib/api/kpis';
export * from '../../../lib/api/medical-workflow';
export * from '../../../lib/api/exports';
export * from '../../../lib/api/backend-health';
