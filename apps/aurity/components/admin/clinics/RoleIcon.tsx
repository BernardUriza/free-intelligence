/**
 * RoleIcon Component
 *
 * Renders a role-appropriate icon for clinic members.
 * Single Responsibility: Visual representation of ClinicRole.
 *
 * Card: FI-CHECKIN-002
 */

import { Crown, Shield, Stethoscope, User } from 'lucide-react';
import type { ClinicRole } from '@/lib/api/clinics';

interface RoleIconProps {
  role: ClinicRole | null;
}

export function RoleIcon({ role }: RoleIconProps) {
  switch (role) {
    case 'OWNER':
      return <Crown className="clinic-role-icon text-yellow-400" />;
    case 'ADMIN':
      return <Shield className="clinic-role-icon fi-text-primary" />;
    case 'DOCTOR':
      return <Stethoscope className="clinic-role-icon fi-text-green" />;
    case 'STAFF':
      return <User className="clinic-role-icon text-slate-400" />;
    default:
      return <User className="clinic-role-icon text-slate-400" />;
  }
}
