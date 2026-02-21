/**
 * ClinicsModals
 *
 * Single Responsibility: Renders all modal dialogs for the Clinics Admin page.
 * Receives visibility flags, data, and handlers from the parent orchestrator.
 *
 * Card: FI-CHECKIN-002
 */

'use client';

import { CreateClinicModal } from '@/components/admin/clinics/CreateClinicModal';
import { LinkToClinicModal } from '@/components/admin/clinics/LinkToClinicModal';
import { DoctorDetailModal } from '@/components/admin/clinics/DoctorDetailModal';
import { CreateDoctorModal } from '@/components/admin/clinics/CreateDoctorModal';
import type { Clinic, ClinicCreate, Doctor } from '@/lib/api/clinics';
import type { DoctorSaveData } from '@/components/admin/clinics/DoctorDetailModal';

interface ClinicsModalsProps {
  // Create Clinic
  showCreateModal: boolean;
  onCloseCreateClinic: () => void;
  onCreateClinic: (data: ClinicCreate) => Promise<void>;

  // Link to Clinic
  showLinkModal: boolean;
  selectedClinic: Clinic | null;
  linkingToClinic: boolean;
  onLinkToClinic: (form: { nombre: string; apellido: string; especialidad: string; role: string }) => Promise<boolean | undefined>;
  onCloseLinkToClinic: () => void;

  // Edit Doctor
  showEditDoctorModal: boolean;
  editingDoctor: Doctor | null;
  onCloseEditDoctor: () => void;
  onSaveDoctor: (data: DoctorSaveData) => Promise<void>;

  // Create Doctor
  showCreateDoctorModal: boolean;
  onCloseCreateDoctor: () => void;
  onDoctorCreated: (doctor: Doctor) => void;
}

export function ClinicsModals({
  showCreateModal,
  onCloseCreateClinic,
  onCreateClinic,
  showLinkModal,
  selectedClinic,
  linkingToClinic,
  onLinkToClinic,
  onCloseLinkToClinic,
  showEditDoctorModal,
  editingDoctor,
  onCloseEditDoctor,
  onSaveDoctor,
  showCreateDoctorModal,
  onCloseCreateDoctor,
  onDoctorCreated,
}: ClinicsModalsProps) {
  return (
    <>
      {showCreateModal && (
        <CreateClinicModal
          onClose={onCloseCreateClinic}
          onCreate={onCreateClinic}
        />
      )}

      {showLinkModal && selectedClinic && (
        <LinkToClinicModal
          clinicName={selectedClinic.name}
          linking={linkingToClinic}
          onSubmit={onLinkToClinic}
          onClose={onCloseLinkToClinic}
        />
      )}

      {showEditDoctorModal && editingDoctor && (
        <DoctorDetailModal
          doctor={editingDoctor}
          onClose={onCloseEditDoctor}
          onSave={onSaveDoctor}
          mode="edit"
        />
      )}

      {showCreateDoctorModal && selectedClinic && (
        <CreateDoctorModal
          clinicId={selectedClinic.clinic_id}
          clinicName={selectedClinic.name}
          onClose={onCloseCreateDoctor}
          onCreate={onDoctorCreated}
        />
      )}
    </>
  );
}
