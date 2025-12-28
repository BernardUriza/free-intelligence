/**
 * @aurity-standalone/api-client
 *
 * Type-safe HTTP client for Aurity backend API.
 * Provides functions for all backend endpoints with proper error handling,
 * SSE support for streaming, and HIPAA-compliant logging.
 *
 * @packageDocumentation
 */

// Core client utilities
export * from './client';

// API modules
export * from './assistant';
export * from './personas';
export * from './llm-models';
export * from './knowledge';
export * from './checkin';
export * from './chat-history';
export * from './timeline';
export * from './kpis';
export * from './medical-workflow';
export * from './exports';
export * from './backend-health';
