/**
 * Clinics Admin Page
 *
 * Admin panel for managing clinics, doctors, and appointments.
 * Route: /admin/clinics
 *
 * Architecture: Thin orchestrator page that composes modular components.
 * - useClinicsAdmin: Data layer (composed from useClinics, useClinicDetails, useClinicMembership)
 * - useClinicModals: Modal visibility state and handlers
 * - ClinicListSidebar: Left panel clinic list
 * - ClinicDetailPanel: Right panel clinic details
 * - ClinicsModals: All modal renderings
 *
 * Card: FI-CHECKIN-002
 */

'use client';

import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { adminClinicsHeader } from '@/config/page-headers';
import { ClinicListSidebar } from '@/components/admin/clinics/ClinicListSidebar';
import { ClinicDetailPanel } from '@/components/admin/clinics/ClinicDetailPanel';
import { useClinicsAdmin } from '@/hooks/useClinicsAdmin';
import { useClinicModals } from './hooks/useClinicModals';
import { ClinicsModals } from './components/ClinicsModals';

export default function ClinicsAdminPage() {
  const {
    user,
    isSuperAdmin,
    clinics,
    loading,
    error,
    selectedClinic,
    loadClinics,
    loadClinicDetails,
    handleCreateClinic,
    handleDeleteClinic,
    doctors,
    doctorLimits,
    handleUpdateDoctor,
    handleDoctorCreated,
    reloadDoctorLimits,
    appointments,
    loadingDetails,
    membership,
    linkingToClinic,
    handleLinkToClinic,
  } = useClinicsAdmin();

  const modals = useClinicModals({
    onUpdateDoctor: handleUpdateDoctor,
    onCreateClinic: handleCreateClinic,
  });

  const headerConfig = adminClinicsHeader({ clinicsCount: clinics.length });

  return (
    <AppTemplate
      headerConfig={headerConfig}
      headerActions={
        <Button onClick={modals.openCreateClinic} variant="indigo" icon={Plus}>
          Nueva Clínica
        </Button>
      }
      backgroundGradient="purple"
      padding="8"
      showWatermark={true}
      showGeometricBg={true}
    >
      <div className="clinic-grid">
        <ClinicListSidebar
          clinics={clinics}
          selectedClinicId={selectedClinic?.clinic_id ?? null}
          loading={loading}
          error={error}
          onSelectClinic={loadClinicDetails}
          onRetry={loadClinics}
        />

        <ClinicDetailPanel
          clinic={selectedClinic}
          doctors={doctors}
          appointments={appointments}
          doctorLimits={doctorLimits}
          loadingDetails={loadingDetails}
          user={user}
          isSuperAdmin={isSuperAdmin}
          membership={membership}
          onDeleteClinic={handleDeleteClinic}
          onEditDoctor={modals.openEditDoctor}
          onAddDoctor={modals.openCreateDoctor}
          onLinkToClinic={modals.openLinkToClinic}
          onReloadDoctorLimits={reloadDoctorLimits}
        />
      </div>

      <ClinicsModals
        showCreateModal={modals.showCreateModal}
        onCloseCreateClinic={modals.closeCreateClinic}
        onCreateClinic={modals.handleCreateClinicAndClose}
        showLinkModal={modals.showLinkModal}
        selectedClinic={selectedClinic}
        linkingToClinic={linkingToClinic}
        onLinkToClinic={handleLinkToClinic}
        onCloseLinkToClinic={modals.closeLinkToClinic}
        showEditDoctorModal={modals.showEditDoctorModal}
        editingDoctor={modals.editingDoctor}
        onCloseEditDoctor={modals.closeEditDoctor}
        onSaveDoctor={modals.handleSaveDoctor}
        showCreateDoctorModal={modals.showCreateDoctorModal}
        onCloseCreateDoctor={modals.closeCreateDoctor}
        onDoctorCreated={handleDoctorCreated}
      />
    </AppTemplate>
  );
}
