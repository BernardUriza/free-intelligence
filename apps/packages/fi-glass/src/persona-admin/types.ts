export interface PersonaExample {
  input: string;
  output: string | Record<string, unknown>;
}

export interface PersonaUsageStats {
  total_invocations: number;
  avg_latency_ms: number;
  avg_cost_usd: number;
}

export interface Persona {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model: string;
  voice?: string | null;
  temperature: number;
  max_tokens: number;
  examples: PersonaExample[];
  usage_stats?: PersonaUsageStats;
  version?: number;
  last_updated?: string;
  updated_by?: string;
}

export interface PersonaCreateRequest {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model?: string;
  voice?: string | null;
  temperature?: number;
  max_tokens?: number;
  examples?: PersonaExample[];
}

export interface PersonaUpdateRequest {
  name?: string;
  description?: string;
  system_prompt?: string;
  model?: string;
  voice?: string | null;
  temperature?: number;
  max_tokens?: number;
  examples?: PersonaExample[];
}

export interface PersonaTestResponse {
  output: string | Record<string, unknown>;
  latency_ms: number;
  tokens_used: number;
  cost_usd: number;
}

/**
 * The persistence seam. A consumer wraps its own API client; the components never import one.
 * Rejections should carry a user-facing `Error.message`: it is rendered as-is.
 */
export interface PersonaStore {
  list(): Promise<Persona[]>;
  get(personaId: string): Promise<Persona>;
  create(request: PersonaCreateRequest): Promise<Persona>;
  update(personaId: string, request: PersonaUpdateRequest): Promise<Persona>;
  remove(personaId: string): Promise<void>;
  test(personaId: string, input: string): Promise<PersonaTestResponse>;
}

export interface PersonaOption {
  value: string;
  label: string;
  /** Rendered as an `<optgroup>` label; options sharing it are grouped. */
  group?: string;
}

export type PersonaHideableField = 'voice' | 'temperature' | 'max_tokens' | 'examples';

export type PersonaConfirm = (message: string) => Promise<boolean>;

export const defaultPersonaConfirm: PersonaConfirm = async (message) =>
  typeof window !== 'undefined' && typeof window.confirm === 'function' ? window.confirm(message) : false;

export function errorMessage(err: unknown, fallback: string): string {
  return err instanceof Error && err.message ? err.message : fallback;
}
