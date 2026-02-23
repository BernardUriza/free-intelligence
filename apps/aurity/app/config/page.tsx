'use client';

/**
 * System Configuration Page
 * SUPERADMIN ONLY — Uses RBAC hook for access control.
 *
 * Composition root that wires useConfigPage to section/modal components.
 * All state lives in the hook; each card is a separate, independently
 * testable component.
 *
 * SOLID principles applied:
 *  - SRP: state in useConfigPage, persistence in hook, UI in sections
 *  - OCP: new sections/modals added without modifying existing ones
 *  - ISP: each section receives only Props it needs (Pick-style interfaces)
 *  - DIP: sections depend on callback interfaces, not state implementation
 *
 * @refactored 2026-02-22
 */

import { AppTemplate } from '@/components/layout/AppTemplate';
import { configHeader } from '@/config/page-headers';
import { UserManagement } from '@/components/admin/user-management';
import { useConfigPage } from './_components';
import {
  SuperadminBanner,
  SystemSettingsSection,
  FeatureFlagsSection,
  SecuritySection,
  RolesManagementSection,
} from './_components/sections';
import { RolesModal, AuditModal } from './_components/modals';

export default function ConfigPage() {
  const {
    user,
    isAuthenticated,
    isSuperAdmin,
    isLoading,
    roles,
    resettingOnboarding,
    handleResetOnboarding,
    showUserManagement,
    setShowUserManagement,
    showRolesModal,
    setShowRolesModal,
    showAuditModal,
    setShowAuditModal,
  } = useConfigPage();

  // --- Loading gate ---
  if (isLoading) {
    return (
      <div className="layout-loading-screen">
        <div className="cfg-loading-spinner" />
      </div>
    );
  }

  // --- Access gate (redirect handled in useConfigPage) ---
  if (!isAuthenticated || !isSuperAdmin) {
    return null;
  }

  const headerConfig = configHeader();

  return (
    <AppTemplate
      headerConfig={headerConfig}
      maxWidth="full"
      padding="0"
      showWatermark
      showGeometricBg
    >
      <div className="cfg-page-container">
        <SuperadminBanner email={user?.email} />

        <div className="cfg-sections">
          <SystemSettingsSection
            resettingOnboarding={resettingOnboarding}
            onResetOnboarding={handleResetOnboarding}
          />

          <FeatureFlagsSection />

          <SecuritySection
            onOpenUserManagement={() => setShowUserManagement(true)}
            onOpenRolesModal={() => setShowRolesModal(true)}
            onOpenAuditModal={() => setShowAuditModal(true)}
          />

          <RolesManagementSection
            email={user?.email}
            userId={user?.sub}
            isSuperAdmin={isSuperAdmin}
            roles={roles}
          />
        </div>
      </div>

      {/* Modals */}
      {showUserManagement && (
        <UserManagement onClose={() => setShowUserManagement(false)} />
      )}
      {showRolesModal && (
        <RolesModal onClose={() => setShowRolesModal(false)} />
      )}
      {showAuditModal && (
        <AuditModal onClose={() => setShowAuditModal(false)} />
      )}
    </AppTemplate>
  );
}
