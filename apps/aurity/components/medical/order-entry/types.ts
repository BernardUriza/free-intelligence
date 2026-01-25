/**
 * OrderEntry Types
 */

import type { LucideIcon } from 'lucide-react';
import type { MedicalOrder } from '@aurity-standalone/api-client/medical-workflow';

export interface OrderEntryProps {
  sessionId: string;
  onNext?: () => void;
  onPrevious?: () => void;
  className?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface OrderTypeConfig {
  label: string;
  icon: LucideIcon;
  color: string;
  gradientClass: string;
  border: string;
  text: string;
}

export type OrderType = MedicalOrder['type'];

export interface NewOrderForm {
  type: OrderType;
  description: string;
  details: string;
}
