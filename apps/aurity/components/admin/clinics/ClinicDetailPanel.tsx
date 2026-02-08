/**
 * ClinicDetailPanel Component
 *
 * Main detail panel for a selected clinic. Orchestrates sub-sections:
 * - Clinic header + info grid
 * - Doctor override editor (superadmin)
 * - Doctors section
 * - Appointments section
 *
 * Single Responsibility: Layout of clinic detail view.
 *
 * Card: FI-CHECKIN-002
 */

import { Building2, Loader2, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ClinicInfoGrid } from '@/components/admin/clinics/ClinicInfoGrid';
import { DoctorsSection } from '@/components/admin/clinics/DoctorsSection';
import { AppointmentsSection } from '@/components/admin/clinics/AppointmentsSection';
import { DoctorOverrideEditor } from '@/components/admin/clinics/DoctorOverrideEditor';
import type { Clinic, Doctor, ClinicMembership, DoctorLimitInfo, Appointment } from '@/lib/api/clinics';

interface UserInfo {
  sub?: string;
  name?: string;
  email?: string;
}

interface ClinicDetailPanelProps {
  clinic: Clinic | null;
  doctors: Doctor[];
  appointments: Appointment[];
  doctorLimits: DoctorLimitInfo | null;
  loadingDetails: boolean;
  user: UserInfo | null | undefined;
  isSuperAdmin: boolean;
  membership: ClinicMembership | null;
  onDeleteClinic: (clinicId: string) => void;
  onEditDoctor: (doctor: Doctor) => void;
  onAddDoctor: () => void;
  onLinkToClinic: () => void;
  onReloadDoctorLimits: () => void;
}

export function ClinicDetailPanel({
  clinic,
  doctors,
  appointments,
  doctorLimits,
  loadingDetails,
  user,
  isSuperAdmin,
  membership,
  onDeleteClinic,
  onEditDoctor,
  onAddDoctor,
  onLinkToClinic,
  onReloadDoctorLimits,
}: ClinicDetailPanelProps) {
  if (!clinic) {
    return (
      <div className="clinic-main">
        <div className="clinic-placeholder">
          <Building2 className="clinic-placeholder-icon" />
          <p>Selecciona una clínica para ver sus detalles</p>
        </div>
      </div>
    );
  }

  return (
    <div className="clinic-main">
      <div className="clinic-detail">
        {/* Header */}
        <div className="clinic-detail-header">
          <div>
            <h2 className="fi-title-2xl">{clinic.name}</h2>
            <p className="clinic-detail-specialty">{clinic.specialty}</p>
            <p className="clinic-detail-plan">
              Plan: {clinic.subscription_plan}
            </p>
          </div>
          <div className="clinic-detail-actions">
            <Button
              onClick={() => onDeleteClinic(clinic.clinic_id)}
              variant="ghost"
              className="clinic-delete-btn"
              title="Desactivar"
              icon={Trash2}
            />
          </div>
        </div>

        {/* Info Grid */}
        <ClinicInfoGrid clinic={clinic} />

        {/* Doctor Override Editor (Superadmin only) */}
        {isSuperAdmin && doctorLimits && (
          <div className="mb-6">
            <DoctorOverrideEditor
              clinicId={clinic.clinic_id}
              clinicName={clinic.name}
              limits={doctorLimits}
              isSuperAdmin={isSuperAdmin}
              onUpdate={onReloadDoctorLimits}
            />
          </div>
        )}

        {loadingDetails ? (
          <div className="clinic-loading">
            <Loader2 className="clinic-loading-icon" />
          </div>
        ) : (
          <>
            <DoctorsSection
              doctors={doctors}
              doctorLimits={doctorLimits}
              clinicId={clinic.clinic_id}
              user={user}
              isSuperAdmin={isSuperAdmin}
              membership={membership}
              onEditDoctor={onEditDoctor}
              onAddDoctor={onAddDoctor}
              onLinkToClinic={onLinkToClinic}
            />
            <AppointmentsSection appointments={appointments} />
          </>
        )}
      </div>
    </div>
  );
}
