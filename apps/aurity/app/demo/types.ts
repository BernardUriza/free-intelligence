export interface DemoSession {
  id: string;
  type: 'medical' | 'legal' | 'code';
  title: string;
  description: string;
  eventCount: number;
  events: DemoEvent[];
  created_at: string;
}

export interface DemoEvent {
  id: string;
  type: string;
  content: string;
  speaker?: string;
  timestamp: number;
  metadata?: Record<string, unknown>;
}

export type ConfirmAction = 'load' | 'reset' | null;

export interface StatusMessage {
  type: 'success' | 'error';
  text: string;
}
