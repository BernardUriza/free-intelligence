/**
 * Config Page Types
 *
 * Shared interfaces for the system configuration page components.
 */

// ---------------------------------------------------------------------------
// Feature Flags
// ---------------------------------------------------------------------------

export interface FeatureFlag {
  readonly label: string;
  readonly description: string;
  readonly active: boolean;
}

// ---------------------------------------------------------------------------
// Permission Matrix
// ---------------------------------------------------------------------------

export interface PermissionRow {
  readonly label: string;
  readonly superadmin: boolean;
  readonly clinician: boolean;
}

// ---------------------------------------------------------------------------
// System Setting Row
// ---------------------------------------------------------------------------

export interface SystemSetting {
  readonly label: string;
  readonly description: string;
  readonly action: 'button' | 'reset';
  readonly buttonLabel: string;
  readonly buttonVariant: 'primary' | 'secondary' | 'danger';
}

// ---------------------------------------------------------------------------
// Component Props (ISP — each component takes only what it needs)
// ---------------------------------------------------------------------------

export interface SuperadminBannerProps {
  readonly email: string | undefined;
}

export interface SystemSettingsSectionProps {
  readonly resettingOnboarding: boolean;
  readonly onResetOnboarding: () => void;
}

export interface RolesManagementSectionProps {
  readonly email: string | undefined;
  readonly userId: string | undefined;
  readonly isSuperAdmin: boolean;
  readonly roles: readonly string[];
}

export interface SecuritySectionProps {
  readonly onOpenUserManagement: () => void;
  readonly onOpenRolesModal: () => void;
  readonly onOpenAuditModal: () => void;
}

export interface ModalProps {
  readonly onClose: () => void;
}
