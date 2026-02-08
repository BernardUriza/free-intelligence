/**
 * DoctorsSection Component
 *
 * Renders the doctors list with member banners, doctor rows, and action buttons.
 * Single Responsibility: Doctor management UI within a clinic.
 *
 * Card: FI-CHECKIN-002
 */

import { Users, Plus, UserPlus, Crown, Check, Pencil } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { RoleIcon } from '@/components/admin/clinics/RoleIcon';
import { DoctorLimitBadge } from '@/components/admin/clinics/DoctorLimitBadge';
import type { Doctor, ClinicMembership, DoctorLimitInfo } from '@/lib/api/clinics';

interface UserInfo {
  sub?: string;
  name?: string;
  email?: string;
}

interface DoctorsSectionProps {
  doctors: Doctor[];
  doctorLimits: DoctorLimitInfo | null;
  clinicId: string;
  user: UserInfo | null | undefined;
  isSuperAdmin: boolean;
  membership: ClinicMembership | null;
  onEditDoctor: (doctor: Doctor) => void;
  onAddDoctor: () => void;
  onLinkToClinic: () => void;
}

export function DoctorsSection({
  doctors,
  doctorLimits,
  clinicId,
  user,
  isSuperAdmin,
  membership,
  onEditDoctor,
  onAddDoctor,
  onLinkToClinic,
}: DoctorsSectionProps) {
  return (
    <div className="mb-6">
      {/* Header */}
      <div className="clinic-section-header">
        <div className="clinic-section-title-group">
          <h3 className="clinic-section-title">
            <Users className="clinic-section-icon" />
            Doctores
          </h3>
          {doctorLimits && (
            <DoctorLimitBadge
              clinicId={clinicId}
              limits={doctorLimits}
              compact
            />
          )}
        </div>
        <div className="clinic-section-actions">
          <Button
            size="sm"
            variant="outline"
            onClick={onAddDoctor}
            disabled={doctorLimits ? !doctorLimits.can_add : false}
            className="clinic-doctor-add-btn"
          >
            <Plus className="clinic-btn-icon" />
            Agregar Doctor
          </Button>
          {user && !membership && !isSuperAdmin && (
            <Button
              size="sm"
              variant="outline"
              onClick={onLinkToClinic}
              className="clinic-doctor-link-btn"
            >
              <UserPlus className="clinic-btn-icon" />
              Vincularme
            </Button>
          )}
        </div>
      </div>

      {/* List */}
      <div className="clinic-doctor-list">
        {/* Superadmin banner */}
        {isSuperAdmin && (
          <SuperadminBanner user={user} />
        )}

        {/* Linked user banner */}
        {!isSuperAdmin && membership && membership.clinic_id === clinicId && (
          <LinkedUserBanner membership={membership} />
        )}

        {/* Other doctors */}
        {doctors
          .filter((d) => d.user_id !== user?.sub)
          .map((doctor) => (
            <DoctorRow
              key={doctor.doctor_id}
              doctor={doctor}
              onEdit={() => onEditDoctor(doctor)}
            />
          ))}

        {doctors.length === 0 && !membership && !isSuperAdmin && (
          <p className="clinic-empty-text">No hay doctores registrados</p>
        )}
      </div>
    </div>
  );
}

// ── Sub-components (private to this module) ─────────────────────────

function SuperadminBanner({ user }: { user: UserInfo | null | undefined }) {
  return (
    <div className="clinic-member-banner-superadmin">
      <div className="fi-flex-gap-md">
        <div className="fi-icon-box-yellow">
          <Crown className="clinic-role-icon-lg text-yellow-400" />
        </div>
        <div>
          <div className="fi-flex-gap">
            <p className="clinic-member-name">{user?.name || user?.email}</p>
            <span className="clinic-badge-superadmin">Superadmin</span>
          </div>
          <p className="fi-subtitle">Acceso completo a todas las clínicas</p>
        </div>
      </div>
      <div className="text-right">
        <span className="clinic-member-email-yellow">{user?.email}</span>
      </div>
    </div>
  );
}

function LinkedUserBanner({ membership }: { membership: ClinicMembership }) {
  return (
    <div className="clinic-member-banner-linked">
      <div className="fi-flex-gap-md">
        <div className="fi-icon-box-emerald">
          <RoleIcon role={membership.clinic_role} />
        </div>
        <div>
          <div className="fi-flex-gap">
            <p className="clinic-member-name">{membership.display_name}</p>
            <span className="clinic-badge-self">Tú</span>
          </div>
          <p className="fi-subtitle">
            {membership.especialidad || 'General'} • {membership.clinic_role}
          </p>
        </div>
      </div>
      <div className="text-right">
        <span className="clinic-member-email-green">{membership.email}</span>
      </div>
    </div>
  );
}

function DoctorRow({ doctor, onEdit }: { doctor: Doctor; onEdit: () => void }) {
  return (
    <div className={!doctor.is_active ? 'clinic-doctor-row-inactive' : 'clinic-doctor-row'}>
      <div className="fi-flex-gap-md">
        <div className="fi-icon-box-slate">
          <RoleIcon role={doctor.clinic_role} />
        </div>
        <div>
          <div className="fi-flex-gap">
            <p className="clinic-doctor-name">{doctor.display_name}</p>
            {doctor.is_linked && (
              <Check className="clinic-linked-check" />
            )}
          </div>
          <p className="fi-subtitle">
            {doctor.especialidad} • {doctor.avg_consultation_minutes} min/consulta
            {doctor.work_start_time && doctor.work_end_time && (
              <span> • {doctor.work_start_time} - {doctor.work_end_time}</span>
            )}
          </p>
        </div>
      </div>
      <div className="fi-flex-gap">
        <Button
          onClick={onEdit}
          variant="ghost"
          size="sm"
          className="clinic-doctor-edit-btn"
          title="Editar horario"
          icon={Pencil}
        />
        <div className="clinic-doctor-meta">
          {doctor.cedula_profesional && (
            <span className="fi-text-xs-muted">
              Cédula: {doctor.cedula_profesional}
            </span>
          )}
          {doctor.email && (
            <p className="fi-text-xs-muted">{doctor.email}</p>
          )}
        </div>
      </div>
    </div>
  );
}
