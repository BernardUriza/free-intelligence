/**
 * UserManagement Types
 */

import type { ClinicRole, AdminUserClinicInfo } from '@/lib/api/clinics';
import type { Role } from '@aurity-standalone/hooks/useRBAC';

export interface User {
  user_id: string;
  email: string;
  name?: string;
  picture?: string;
  created_at: string;
  last_login?: string;
  logins_count?: number;
  roles: Role[];
  blocked?: boolean;
  clinicInfo?: AdminUserClinicInfo;
}

export interface UserManagementProps {
  onClose: () => void;
  asPage?: boolean;
}

export const CLINIC_ROLES: { value: ClinicRole; label: string }[] = [
  { value: 'OWNER', label: 'Propietario' },
  { value: 'ADMIN', label: 'Administrador' },
  { value: 'DOCTOR', label: 'Doctor' },
  { value: 'STAFF', label: 'Staff' },
];

// Re-export for convenience
export type { ClinicRole, AdminUserClinicInfo, Role };
