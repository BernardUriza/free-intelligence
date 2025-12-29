'use client';

/**
 * Admin License Generator Page
 *
 * Superadmin-only page for generating Aurity Desktop license keys.
 * Protected by FI-superadmin role requirement.
 *
 * Route: /admin/licenses
 */

import { AppTemplate } from '@/components/layout/AppTemplate';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { adminLicensesHeader } from '@/config/page-headers';
import { LicenseGenerator } from '@/components/admin/license-generator';

export default function LicensesAdminPage() {
  const headerConfig = adminLicensesHeader();

  return (
    <ProtectedRoute requireRoles={['FI-superadmin']}>
      <AppTemplate
        headerConfig={headerConfig}
        backgroundGradient="slate"
        padding="6"
        maxWidth="5xl"
      >
        <div className="py-6">
          <LicenseGenerator />
        </div>
      </AppTemplate>
    </ProtectedRoute>
  );
}
