'use client';

/**
 * User Management Page
 * Route: /admin/users
 *
 * Admin panel for managing users and clinic assignments.
 * Requires FI-superadmin role.
 */

import { useRouter } from 'next/navigation';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { adminUsersHeader } from '@/config/page-headers';
import { UserManagement } from '@/components/admin/user-management';

export default function UsersAdminPage() {
  const router = useRouter();
  const headerConfig = adminUsersHeader({});

  return (
    <AppTemplate
      headerConfig={headerConfig}
      backgroundGradient="slate"
      padding="0"
      maxWidth="full"
    >
      <UserManagement
        onClose={() => router.push('/')}
        asPage={true}
      />
    </AppTemplate>
  );
}
