/**
 * Clinics Admin Page
 *
 * Admin panel for managing clinics, doctors, and appointments.
 * Route: /admin/clinics
 *
 * Architecture: Thin orchestrator page that composes modular components.
 * - useClinicsAdmin: All state + data fetching
 * - ClinicListSidebar: Left panel clinic list
 * - ClinicDetailPanel: Right panel clinic details
 * - CreateClinicModal / LinkToClinicModal: Modal forms
 * - DoctorDetailModal / CreateDoctorModal: Doctor modals (pre-existing)
 *
 * Card: FI-CHECKIN-002
 */

'use client';

import { useState, useCallback } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { adminClinicsHeader } from '@/config/page-headers';
import { ClinicListSidebar } from '@/components/admin/clinics/ClinicListSidebar';
import { ClinicDetailPanel } from '@/components/admin/clinics/ClinicDetailPanel';
import { CreateClinicModal } from '@/components/admin/clinics/CreateClinicModal';
import { LinkToClinicModal } from '@/components/admin/clinics/LinkToClinicModal';
import { DoctorDetailModal } from '@/components/admin/clinics/DoctorDetailModal';
import type { DoctorSaveData } from '@/components/admin/clinics/DoctorDetailModal';
import { CreateDoctorModal } from '@/components/admin/clinics/CreateDoctorModal';
import { useClinicsAdmin } from '@/hooks/useClinicsAdmin';
import type { Doctor } from '@/lib/api/clinics';

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

  // Modal visibility state (UI-only, belongs in page)
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [showCreateDoctorModal, setShowCreateDoctorModal] = useState(false);
  const [showEditDoctorModal, setShowEditDoctorModal] = useState(false);
  const [editingDoctor, setEditingDoctor] = useState<Doctor | null>(null);

  // ── Modal handlers ────────────────────────────────────────────────

  const handleEditDoctorClick = useCallback((doctor: Doctor) => {
    setEditingDoctor(doctor);
    setShowEditDoctorModal(true);
  }, []);

  const handleSaveDoctor = useCallback(async (data: DoctorSaveData) => {
    if (!editingDoctor) return;
    await handleUpdateDoctor(editingDoctor, data);
    setShowEditDoctorModal(false);
    setEditingDoctor(null);
  }, [editingDoctor, handleUpdateDoctor]);

  const handleCreateClinicAndClose = useCallback(async (data: Parameters<typeof handleCreateClinic>[0]) => {
    await handleCreateClinic(data);
    setShowCreateModal(false);
  }, [handleCreateClinic]);

  // ── Render ────────────────────────────────────────────────────────

  const headerConfig = adminClinicsHeader({ clinicsCount: clinics.length });

  return (
    <AppTemplate
      headerConfig={headerConfig}
      headerActions={
        <Button onClick={() => setShowCreateModal(true)} variant="indigo" icon={Plus}>
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
          onEditDoctor={handleEditDoctorClick}
          onAddDoctor={() => setShowCreateDoctorModal(true)}
          onLinkToClinic={() => setShowLinkModal(true)}
          onReloadDoctorLimits={reloadDoctorLimits}
        />
      </div>

      {/* ── Modals ─────────────────────────────────────────────────── */}

      {showCreateModal && (
        <CreateClinicModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateClinicAndClose}
        />
      )}

      {showLinkModal && selectedClinic && (
        <LinkToClinicModal
          clinicName={selectedClinic.name}
          linking={linkingToClinic}
          onSubmit={handleLinkToClinic}
          onClose={() => setShowLinkModal(false)}
        />
      )}

      {showEditDoctorModal && editingDoctor && (
        <DoctorDetailModal
          doctor={editingDoctor}
          onClose={() => {
            setShowEditDoctorModal(false);
            setEditingDoctor(null);
          }}
          onSave={handleSaveDoctor}
          mode="edit"
        />
      )}

      {showCreateDoctorModal && selectedClinic && (
        <CreateDoctorModal
          clinicId={selectedClinic.clinic_id}
          clinicName={selectedClinic.name}
          onClose={() => setShowCreateDoctorModal(false)}
          onCreate={handleDoctorCreated}
        />
      )}
    </AppTemplate>
  );
}
