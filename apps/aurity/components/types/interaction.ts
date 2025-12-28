/**
 * Interaction type definition
 * Card: FI-UI-FEAT-205
 *
 * Represents a single interaction (prompt + response) in the system
 */

export interface Interaction {
  id: string;
  session_id: string;
  prompt: string;
  response?: string;
  provider: string;
  model: string;
  latency_ms?: number;
  tokens_in?: number;
  tokens_out?: number;
  content_hash: string;
  manifest_hash?: string;
  created_at: string;
  updated_at?: string;
  metadata?: Record<string, unknown>;
}
