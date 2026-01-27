/**
 * Check-in Action Icons
 *
 * Lucide icons for patient check-in actions.
 * Replaces emojis in checkin.ts for consistency.
 */

import {
  Smartphone,
  Building2,
  PenLine,
  Lock,
  CreditCard,
  Coins,
  TestTube,
  FileX,
  ClipboardList,
  ShieldCheck,
  FileText,
  IdCard,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

/**
 * Check-in action icons mapping
 */
export const CHECKIN_ACTION_ICONS: Record<string, LucideIcon> = {
  update_contact: Smartphone,
  update_insurance: Building2,
  sign_consent: PenLine,
  sign_privacy: Lock,
  pay_copay: CreditCard,
  pay_balance: Coins,
  upload_labs: TestTube,
  upload_imaging: FileX,
  fill_questionnaire: ClipboardList,
  verify_identity: IdCard,
  // Fallback
  default: FileText,
} as const;

/**
 * Check-in status icons
 */
export const CHECKIN_STATUS_ICONS: Record<string, LucideIcon> = {
  completed: ShieldCheck,
  pending: ClipboardList,
  in_progress: FileText,
  required: Lock,
} as const;

/**
 * Get icon for a check-in action type
 * @param actionType - The action type key
 * @returns The corresponding Lucide icon component
 */
export function getCheckinActionIcon(actionType: string): LucideIcon {
  return CHECKIN_ACTION_ICONS[actionType] || CHECKIN_ACTION_ICONS.default;
}

/**
 * Get icon for check-in status
 */
export function getCheckinStatusIcon(status: string): LucideIcon {
  return CHECKIN_STATUS_ICONS[status] || ClipboardList;
}
