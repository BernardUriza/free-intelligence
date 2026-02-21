/**
 * CalendarView
 *
 * Main view when no appointment is active.
 * Shows the doctor's weekly calendar, admin selectors,
 * and all supporting modals (appointment, patient, delete, audit, availability).
 */

'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { medicalAiHeader } from '@/config/page-headers';
import { PatientModal } from '@/components/patients';
import { SessionAuditPanel } from '@/components/medical';
import { AlertCircle, Calendar, Trash2 } from 'lucide-react';
import { DoctorDetailModal, type DoctorSaveData } from '@/components/admin/clinics/DoctorDetailModal';
import type { Appointment } from '@/components/bryntum/utils/appointment-transform.utils';
import type { Doctor, Clinic } from '@/lib/api/clinics';
import type { DoctorAvailability } from '@/components/admin/clinics/availability-designer/types';

import { DoctorAppointmentsCalendar } from '../components/DoctorAppointmentsCalendar';
import { AppointmentModal } from '@/components/appointments';
import { DoctorSelector } from '../components/DoctorSelector';
import { ClinicSelector } from '@/components/shared/ClinicSelector';
import type { AppointmentSubmitData } from '../types';

// ============================================================================
// Types
// ============================================================================

interface CalendarViewProps {
  // Doctor & clinic context
  doctor: Doctor | null;
  membership: { clinic_id: string; clinic_name: string } | null;
  effectiveDoctor: Doctor | null;

  // Admin selectors
  isSuperAdmin: boolean;
  isClinicAdmin: boolean;
  clinics: Clinic[];
  selectedClinicId: string | null;
  loadingClinics: boolean;
  clinicDoctors: Doctor[];
  loadingDoctors: boolean;
  onSelectClinic: (clinic: Clinic) => void;
  onSelectDoctor: (doctor: Doctor) => void;

  // Calendar data
  appointments: Appointment[];
  currentDate: Date;
  onDateChange: (date: Date) => void;
  loadingAppointments: boolean;

  // Appointment actions
  onSelectAppointment: (appointment: Appointment) => void;
  onCreateAppointment: (date: Date) => void;
  showAppointmentModal: boolean;
  onCloseAppointmentModal: () => void;
  onSubmitAppointment: (data: AppointmentSubmitData) => Promise<void>;
  onAfterSubmitAppointment: () => Promise<void>;
  selectedSlotTime: Date | null;

  // Patient modal
  patientsError: string | null;
  showPatientModal: boolean;
  setShowPatientModal: (v: boolean) => void;
  editingPatient: any;
  setEditingPatient: (p: any) => void;

  // Session delete
  deleteConfirmSession: string | null;
  setDeleteConfirmSession: (id: string | null) => void;
  deletingSession: string | null;
  handleDeleteSession: (id: string) => void;

  // Doctor availability modal
  showDoctorModal: boolean;
  setShowDoctorModal: (v: boolean) => void;
  onSaveDoctorAvailability: (data: DoctorSaveData) => Promise<void>;

  // Audit
  auditSessionId: string | null;
  setAuditSessionId: (id: string | null) => void;
}

// ============================================================================
// Component
// ============================================================================

export function CalendarView({
  doctor,
  membership,
  effectiveDoctor,
  isSuperAdmin,
  isClinicAdmin,
  clinics,
  selectedClinicId,
  loadingClinics,
  clinicDoctors,
  loadingDoctors,
  onSelectClinic,
  onSelectDoctor,
  appointments,
  currentDate,
  onDateChange,
  loadingAppointments,
  onSelectAppointment,
  onCreateAppointment,
  showAppointmentModal,
  onCloseAppointmentModal,
  onSubmitAppointment,
  onAfterSubmitAppointment,
  selectedSlotTime,
  patientsError,
  showPatientModal,
  setShowPatientModal,
  editingPatient,
  setEditingPatient,
  deleteConfirmSession,
  setDeleteConfirmSession,
  deletingSession,
  handleDeleteSession,
  showDoctorModal,
  setShowDoctorModal,
  onSaveDoctorAvailability,
  auditSessionId,
  setAuditSessionId,
}: CalendarViewProps) {
  const headerConfig = medicalAiHeader({ subtitle: 'Mis citas de hoy' });

  return (
    <AppTemplate
      headerConfig={headerConfig}
      headerActions={
        doctor && membership && (
          <Button
            onClick={() => setShowDoctorModal(true)}
            variant="outline"
            size="sm"
            icon={Calendar}
          >
            Mi Disponibilidad
          </Button>
        )
      }
      padding="0"
      showWatermark={true}
      showGeometricBg={true}
    >
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Error Loading Patients */}
        {patientsError && (
          <div className="med-error-banner">
            <AlertCircle className="h-5 w-5 fi-text-error flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-red-300">Error al cargar pacientes</p>
              <p className="text-sm fi-text-error mt-1">{patientsError}</p>
            </div>
          </div>
        )}

        {/* Admin Selectors */}
        {isClinicAdmin && (
          <div className="mb-4 flex items-center gap-3 flex-wrap">
            {isSuperAdmin && (
              <>
                <span className="text-sm text-slate-400">Clínica:</span>
                <ClinicSelector
                  clinics={clinics}
                  selectedClinic={clinics.find((c) => c.clinic_id === selectedClinicId) || null}
                  onSelectClinic={onSelectClinic}
                  loading={loadingClinics}
                />
              </>
            )}
            {clinicDoctors.length > 0 && (
              <>
                <span className="text-sm text-slate-400">Doctor:</span>
                <DoctorSelector
                  doctors={clinicDoctors}
                  selectedDoctor={effectiveDoctor}
                  onSelectDoctor={onSelectDoctor}
                  loading={loadingDoctors}
                />
              </>
            )}
          </div>
        )}

        {/* Calendar */}
        {effectiveDoctor ? (
          <div className="med-calendar-container">
            <DoctorAppointmentsCalendar
              appointments={appointments}
              currentDate={currentDate}
              onDateChange={onDateChange}
              onSelectAppointment={onSelectAppointment}
              onCreateAppointment={onCreateAppointment}
              loading={loadingAppointments || loadingDoctors}
              availability={effectiveDoctor.working_hours}
            />
          </div>
        ) : (
          <div className="med-calendar-placeholder">
            <p className="text-slate-400 text-lg">Selecciona un doctor para ver su calendario</p>
          </div>
        )}

        {/* Appointment Modal */}
        <AppointmentModal
          mode="create"
          isOpen={showAppointmentModal}
          onClose={onCloseAppointmentModal}
          onCancel={onCloseAppointmentModal}
          onSubmit={onSubmitAppointment}
          doctors={
            isClinicAdmin && clinicDoctors.length > 0
              ? (clinicDoctors as any[])
              : effectiveDoctor
                ? [effectiveDoctor as any]
                : []
          }
          prefilledData={{
            date: selectedSlotTime || undefined,
            doctorId: effectiveDoctor?.doctor_id,
          }}
          submitButtonText="Crear Cita"
          hideDoctorField={!isClinicAdmin}
          onAfterSubmit={onAfterSubmitAppointment}
        />

        {/* Patient Modal */}
        <PatientModal
          isOpen={showPatientModal || editingPatient !== null}
          mode={editingPatient ? 'edit' : 'create'}
          patient={editingPatient || undefined}
          initialData={
            editingPatient
              ? {
                  nombre: editingPatient.name.split(' ')[0],
                  apellido: editingPatient.name.split(' ').slice(1).join(' '),
                  fecha_nacimiento: editingPatient.fechaNacimiento,
                  curp: editingPatient.curp || null,
                }
              : undefined
          }
          onClose={() => {
            setShowPatientModal(false);
            setEditingPatient(null);
          }}
          onSuccess={() => {
            setShowPatientModal(false);
            setEditingPatient(null);
          }}
        />

        {/* Delete Confirmation Modal */}
        {deleteConfirmSession && (
          <div className="med-delete-backdrop">
            <div className="med-delete-modal">
              <div className="flex items-start gap-4 mb-4">
                <div className="med-danger-icon-box">
                  <Trash2 className="h-6 w-6 fi-text-error" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-white mb-1">Eliminar Sesión</h3>
                  <p className="fi-subtitle">
                    ¿Estás seguro de eliminar esta sesión? Esta acción no se puede deshacer.
                  </p>
                </div>
              </div>

              <div className="bg-slate-900/50 rounded-lg p-3 mb-6">
                <div className="fi-text-xs-muted mb-1">Session ID</div>
                <div className="text-sm font-mono text-white">{deleteConfirmSession}</div>
              </div>

              <div className="flex gap-3">
                <Button
                  onClick={() => setDeleteConfirmSession(null)}
                  disabled={deletingSession !== null}
                  variant="secondary"
                  fullWidth
                >
                  Cancelar
                </Button>
                <Button
                  onClick={() => handleDeleteSession(deleteConfirmSession)}
                  disabled={deletingSession !== null}
                  variant="danger"
                  fullWidth
                  loading={deletingSession === deleteConfirmSession}
                >
                  {deletingSession === deleteConfirmSession ? 'Eliminando...' : 'Eliminar Sesión'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Session Audit Panel */}
        {auditSessionId && (
          <SessionAuditPanel
            sessionId={auditSessionId}
            isOpen={true}
            onClose={() => setAuditSessionId(null)}
            onApprove={() => {
              console.log('[MedicalAI] Session approved:', auditSessionId);
            }}
            onReject={() => {
              console.log('[MedicalAI] Session rejected:', auditSessionId);
            }}
          />
        )}

        {/* Doctor Availability Modal */}
        {showDoctorModal && doctor && (
          <DoctorDetailModal
            doctor={{
              id: doctor.doctor_id,
              doctor_id: doctor.doctor_id,
              name: doctor.display_name || `${doctor.nombre} ${doctor.apellido}`,
              display_name: doctor.display_name,
              specialty: doctor.especialidad || undefined,
              especialidad: doctor.especialidad,
              work_start_time: doctor.work_start_time,
              work_end_time: doctor.work_end_time,
              working_hours: doctor.working_hours,
              email: doctor.email,
              cedula_profesional: doctor.cedula_profesional,
            }}
            onClose={() => setShowDoctorModal(false)}
            onSave={onSaveDoctorAvailability}
            mode="edit"
          />
        )}
      </div>
    </AppTemplate>
  );
}
