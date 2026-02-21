'use client';

/**
 * User Profile Page
 * Composition root — delegates to extracted components and hook.
 */

import Link from 'next/link';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { profileHeader } from '@/config/page-headers';
import { useProfile } from './hooks/useProfile';
import { ProfileCard } from './components/ProfileCard';
import { SettingsSection } from './components/SettingsSection';
import { DiskUsageSection } from './components/DiskUsageSection';
import { DangerZone } from './components/DangerZone';
import { DeleteMemoryModal } from './components/DeleteMemoryModal';

export default function ProfilePage() {
  const {
    user,
    isAuthenticated,
    isLoading,
    diskUsage,
    showDeleteModal,
    setShowDeleteModal,
    isDeleting,
    handleChangePassword,
    handleDeleteLongitudinalMemory,
  } = useProfile();

  if (isLoading) {
    return (
      <div className="layout-loading-screen">
        <div className="prof-spinner"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="layout-loading-screen">
        <div className="prof-unauth-wrapper">
          <p className="prof-unauth-text">Debes iniciar sesión para ver tu perfil</p>
          <Link href="/" className="fi-text-primary prof-unauth-link">
            Volver al inicio
          </Link>
        </div>
      </div>
    );
  }

  const headerConfig = profileHeader({
    email: user?.email,
    emailVerified: user?.email_verified,
    role: user?.roles?.[0] || 'USER',
  });

  return (
    <AppTemplate headerConfig={headerConfig} showWatermark={true} showGeometricBg={true}>
      <main className="prof-main">
        <ProfileCard user={user} />
        <SettingsSection onChangePassword={handleChangePassword} />
        <DiskUsageSection diskUsage={diskUsage} />
        <DangerZone onDeleteClick={() => setShowDeleteModal(true)} />

        {showDeleteModal && (
          <DeleteMemoryModal
            isDeleting={isDeleting}
            onConfirm={handleDeleteLongitudinalMemory}
            onCancel={() => setShowDeleteModal(false)}
          />
        )}
      </main>
    </AppTemplate>
  );
}
