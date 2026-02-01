/**
 * Clinics Admin Page
 *
 * Admin panel for managing clinics, doctors, and appointments.
 * Route: /admin/clinics
 *
 * Card: FI-CHECKIN-002
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import {
  Building2,
  Plus,
  Loader2,
  AlertCircle,
  Users,
  Calendar,
  QrCode,
  CreditCard,
  MessageSquare,
  Pencil,
  Trash2,
  ChevronRight,
  X,
  UserPlus,
  Crown,
  Shield,
  Stethoscope,
  User,
  Check,
} from 'lucide-react';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { adminClinicsHeader } from '@/config/page-headers';
import { useAuth } from '@aurity-standalone/hooks/useAuth';
import { useRBAC } from '@aurity-standalone/hooks/useRBAC';
import type { Clinic, ClinicCreate, Doctor, Appointment, ClinicMembership, ClinicRole, DoctorLimitInfo } from '@/lib/api/clinics';
import {
  fetchClinics,
  createClinic,
  deleteClinic,
  fetchDoctors,
  updateDoctor,
  fetchAppointments,
  getClinicMembership,
  linkToClinic,
  fetchDoctorLimits,
} from '@/lib/api/clinics';
import { confirmDialog, toastError } from '@/lib/swal';
import { DoctorDetailModal } from '@/components/admin/clinics/DoctorDetailModal';
import type { DoctorSaveData } from '@/components/admin/clinics/DoctorDetailModal';
import { CreateDoctorModal } from '@/components/admin/clinics/CreateDoctorModal';
import { DoctorLimitBadge } from '@/components/admin/clinics/DoctorLimitBadge';
import { DoctorOverrideEditor } from '@/components/admin/clinics/DoctorOverrideEditor';

// Role icons helper
const RoleIcon = ({ role }: { role: ClinicRole | null }) => {
  switch (role) {
    case 'OWNER':
      return <Crown className="w-4 h-4 text-yellow-400" />;
    case 'ADMIN':
      return <Shield className="w-4 h-4 fi-text-primary" />;
    case 'DOCTOR':
      return <Stethoscope className="w-4 h-4 fi-text-green" />;
    case 'STAFF':
      return <User className="w-4 h-4 text-slate-400" />;
    default:
      return <User className="w-4 h-4 text-slate-400" />;
  }
};

export default function ClinicsAdminPage() {
  const { user } = useAuth();
  const { isSuperAdmin } = useRBAC();
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedClinic, setSelectedClinic] = useState<Clinic | null>(null);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Doctor edit state
  const [showEditDoctorModal, setShowEditDoctorModal] = useState(false);
  const [editingDoctor, setEditingDoctor] = useState<Doctor | null>(null);

  // User-Clinic membership state
  const [membership, setMembership] = useState<ClinicMembership | null>(null);
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [linkingToClinic, setLinkingToClinic] = useState(false);
  const [linkForm, setLinkForm] = useState({
    nombre: '',
    apellido: '',
    especialidad: '',
    role: 'OWNER' as ClinicRole,
  });

  // Doctor limits and create modal state
  const [doctorLimits, setDoctorLimits] = useState<DoctorLimitInfo | null>(null);
  const [showCreateDoctorModal, setShowCreateDoctorModal] = useState(false);

  // Load clinics on mount
  useEffect(() => {
    loadClinics();
  }, []);

  const loadMembership = useCallback(async () => {
    if (!user?.sub) return;
    try {
      const data = await getClinicMembership(user.sub, user.email ?? undefined);
      setMembership(data);
    } catch (err) {
      console.error('Failed to load membership:', err);
    }
  }, [user?.sub, user?.email]);

  // Load user membership when user is available
  useEffect(() => {
    if (user?.sub) {
      loadMembership();
    }
  }, [user?.sub, loadMembership]);

  const handleLinkToClinic = async () => {
    if (!user?.sub || !selectedClinic) return;

    setLinkingToClinic(true);
    try {
      const result = await linkToClinic(
        user.sub,
        {
          clinic_id: selectedClinic.clinic_id,
          role: linkForm.role,
          nombre: linkForm.nombre,
          apellido: linkForm.apellido,
          especialidad: linkForm.especialidad || undefined,
        },
        user.email ?? undefined
      );

      if (result.success && result.membership) {
        setMembership(result.membership);
        setShowLinkModal(false);
        // Reload doctors to show the new entry
        loadClinicDetails(selectedClinic);
      }
    } catch (err) {
      console.error('Failed to link to clinic:', err);
      toastError(err instanceof Error ? err.message : 'Error al vincularse a la clínica');
    } finally {
      setLinkingToClinic(false);
    }
  };

  const loadClinics = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchClinics(false); // Include inactive
      setClinics(data);
    } catch (err) {
      console.error('Failed to load clinics:', err);
      setError(err instanceof Error ? err.message : 'Error al cargar las clínicas');
    } finally {
      setLoading(false);
    }
  };

  const loadClinicDetails = async (clinic: Clinic) => {
    setSelectedClinic(clinic);
    setLoadingDetails(true);
    try {
      const [doctorsData, appointmentsData, limitsData] = await Promise.all([
        fetchDoctors(clinic.clinic_id, true), // Only show active doctors
        fetchAppointments(clinic.clinic_id),
        fetchDoctorLimits(clinic.clinic_id),
      ]);
      setDoctors(doctorsData);
      setAppointments(appointmentsData);
      setDoctorLimits(limitsData);
    } catch (err) {
      console.error('Failed to load clinic details:', err);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleCreateClinic = async (data: ClinicCreate) => {
    try {
      const newClinic = await createClinic(data);
      setClinics((prev) => [...prev, newClinic]);
      setShowCreateModal(false);
    } catch (err) {
      console.error('Failed to create clinic:', err);
      throw err;
    }
  };

  const handleDeleteClinic = async (clinicId: string) => {
    const confirmed = await confirmDialog({
      title: '¿Desactivar clínica?',
      text: 'La clínica será desactivada pero no se eliminará permanentemente.',
      confirmText: 'Desactivar',
      icon: 'warning',
    });
    if (!confirmed) return;
    try {
      await deleteClinic(clinicId);
      setClinics((prev) =>
        prev.map((c) => (c.clinic_id === clinicId ? { ...c, is_active: false } : c))
      );
      if (selectedClinic?.clinic_id === clinicId) {
        setSelectedClinic(null);
      }
    } catch (err) {
      console.error('Failed to delete clinic:', err);
    }
  };

  const handleEditDoctorClick = (doctor: Doctor) => {
    setEditingDoctor(doctor);
    setShowEditDoctorModal(true);
  };

  const handleUpdateDoctor = async (data: DoctorSaveData) => {
    if (!editingDoctor || !selectedClinic) return;
    try {
      const updated = await updateDoctor(
        selectedClinic.clinic_id,
        editingDoctor.doctor_id,
        data
      );
      setDoctors((prev) =>
        prev.map((d) => (d.doctor_id === updated.doctor_id ? updated : d))
      );
      setShowEditDoctorModal(false);
      setEditingDoctor(null);
    } catch (err) {
      console.error('Failed to update doctor:', err);
      toastError(err instanceof Error ? err.message : 'Error al actualizar doctor');
    }
  };

  const headerConfig = adminClinicsHeader({ clinicsCount: clinics.length });

  return (
    <AppTemplate
      headerConfig={headerConfig}
      headerActions={
        <Button
          onClick={() => setShowCreateModal(true)}
          variant="indigo"
          icon={Plus}
        >
          Nueva Clínica
        </Button>
      }
      backgroundGradient="purple"
      padding="8"
      showWatermark={true}
      showGeometricBg={true}
    >

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Clinics List */}
          <div className="lg:col-span-1 space-y-4">
            <h2 className="fi-title mb-4">Clínicas</h2>

            {/* Loading State */}
            {loading && (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
              </div>
            )}

            {/* Error State */}
            {error && !loading && (
              <div className="p-4 bg-red-950/20 border border-red-800 rounded-lg">
                <div className="fi-flex-gap">
                  <AlertCircle className="w-5 h-5 fi-text-error" />
                  <span className="text-red-300 text-sm">{error}</span>
                </div>
                <Button
                  onClick={loadClinics}
                  variant="ghost"
                  size="sm"
                  className="mt-2 fi-text-error hover:text-red-300"
                >
                  Reintentar
                </Button>
              </div>
            )}

            {/* Clinics List */}
            {!loading && !error && clinics.map((clinic) => (
              <div
                key={clinic.clinic_id}
                onClick={() => loadClinicDetails(clinic)}
                className={`p-4 rounded-lg border cursor-pointer transition-all ${
                  selectedClinic?.clinic_id === clinic.clinic_id
                    ? 'bg-indigo-950/50 border-indigo-500'
                    : 'bg-slate-900/50 border-slate-700 hover:border-slate-600'
                } ${!clinic.is_active ? 'opacity-50' : ''}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="font-medium text-white">{clinic.name}</h3>
                    <p className="fi-subtitle">{clinic.specialty}</p>
                    <div className="fi-flex-gap mt-2">
                      {clinic.checkin_qr_enabled && (
                        <span title="QR Check-in"><QrCode className="w-4 h-4 fi-text-green" /></span>
                      )}
                      {clinic.payments_enabled && (
                        <span title="Pagos"><CreditCard className="w-4 h-4 text-yellow-400" /></span>
                      )}
                      {clinic.chat_enabled && (
                        <span title="Chat"><MessageSquare className="w-4 h-4 fi-text-primary" /></span>
                      )}
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-500" />
                </div>
                {!clinic.is_active && (
                  <span className="text-xs fi-text-error mt-2 block">Inactiva</span>
                )}
              </div>
            ))}

            {!loading && !error && clinics.length === 0 && (
              <div className="fi-empty-state-subtle">
                No hay clínicas registradas
              </div>
            )}
          </div>

          {/* Clinic Details Panel */}
          <div className="lg:col-span-2">
            {selectedClinic ? (
              <div className="bg-slate-900/50 rounded-lg border border-slate-700 p-6">
                {/* Clinic Header */}
                <div className="flex items-start justify-between mb-6">
                  <div>
                    <h2 className="fi-title-2xl">{selectedClinic.name}</h2>
                    <p className="text-slate-400">{selectedClinic.specialty}</p>
                    <p className="text-sm text-slate-500 mt-1">
                      Plan: {selectedClinic.subscription_plan}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => handleDeleteClinic(selectedClinic.clinic_id)}
                      variant="ghost"
                      className="fi-text-error hover:bg-red-950/50"
                      title="Desactivar"
                      icon={Trash2}
                    />
                  </div>
                </div>

                {/* Clinic Info */}
                <div className="grid grid-cols-2 gap-4 mb-6 p-4 bg-slate-800/50 rounded-lg">
                  <div>
                    <span className="text-sm text-slate-500">Zona horaria</span>
                    <p className="text-white">{selectedClinic.timezone}</p>
                  </div>
                  <div>
                    <span className="text-sm text-slate-500">Color primario</span>
                    <div className="fi-flex-gap">
                      <div
                        className="w-6 h-6 rounded"
                        style={{ backgroundColor: selectedClinic.primary_color || '#6366f1' }}
                      />
                      <span className="text-white">{selectedClinic.primary_color}</span>
                    </div>
                  </div>
                  <div className="col-span-2">
                    <span className="text-sm text-slate-500">Mensaje de bienvenida</span>
                    <p className="text-white">{selectedClinic.welcome_message || '-'}</p>
                  </div>
                </div>

                {/* Doctor Override Editor (Superadmin only) */}
                {isSuperAdmin && doctorLimits && (
                  <div className="mb-6">
                    <DoctorOverrideEditor
                      clinicId={selectedClinic.clinic_id}
                      clinicName={selectedClinic.name}
                      limits={doctorLimits}
                      isSuperAdmin={isSuperAdmin}
                      onUpdate={() => {
                        fetchDoctorLimits(selectedClinic.clinic_id).then(setDoctorLimits);
                      }}
                    />
                  </div>
                )}

                {loadingDetails ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
                  </div>
                ) : (
                  <>
                    {/* Doctors Section */}
                    <div className="mb-6">
                      <div className="fi-flex-between mb-3">
                        <div className="flex items-center gap-3">
                          <h3 className="fi-title fi-flex-gap">
                            <Users className="w-5 h-5 text-indigo-400" />
                            Doctores
                          </h3>
                          {doctorLimits && (
                            <DoctorLimitBadge
                              clinicId={selectedClinic.clinic_id}
                              limits={doctorLimits}
                              compact
                            />
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {/* Add Doctor button */}
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setShowCreateDoctorModal(true)}
                            disabled={doctorLimits ? !doctorLimits.can_add : false}
                            className="fi-text-primary border-indigo-400/50 hover:bg-indigo-400/10 disabled:opacity-50"
                          >
                            <Plus className="w-4 h-4 mr-2" />
                            Agregar Doctor
                          </Button>
                          {/* Link to clinic button - only for non-superadmin users who aren't linked */}
                          {user && !membership && !isSuperAdmin && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setShowLinkModal(true)}
                              className="fi-text-success border-emerald-400/50 hover:bg-emerald-400/10"
                            >
                              <UserPlus className="w-4 h-4 mr-2" />
                              Vincularme
                            </Button>
                          )}
                        </div>
                      </div>
                      <div className="space-y-2">
                        {/* Show superadmin banner if user is superadmin */}
                        {isSuperAdmin && (
                          <div className="p-3 bg-yellow-900/30 border border-yellow-500/30 rounded-lg fi-flex-between">
                            <div className="fi-flex-gap-md">
                              <div className="fi-icon-box-yellow">
                                <Crown className="w-5 h-5 text-yellow-400" />
                              </div>
                              <div>
                                <div className="fi-flex-gap">
                                  <p className="text-white font-medium">{user?.name || user?.email}</p>
                                  <span className="px-2 py-0.5 text-xs bg-yellow-500/20 text-yellow-400 rounded-full font-medium">
                                    Superadmin
                                  </span>
                                </div>
                                <p className="fi-subtitle">
                                  Acceso completo a todas las clínicas
                                </p>
                              </div>
                            </div>
                            <div className="text-right">
                              <span className="text-xs text-yellow-400">{user?.email}</span>
                            </div>
                          </div>
                        )}

                        {/* Show current user if they are linked to this clinic (non-superadmin) */}
                        {!isSuperAdmin && membership && membership.clinic_id === selectedClinic.clinic_id && (
                          <div className="p-3 bg-emerald-900/30 border border-emerald-500/30 rounded-lg fi-flex-between">
                            <div className="fi-flex-gap-md">
                              <div className="fi-icon-box-emerald">
                                <RoleIcon role={membership.clinic_role} />
                              </div>
                              <div>
                                <div className="fi-flex-gap">
                                  <p className="text-white font-medium">{membership.display_name}</p>
                                  <span className="px-2 py-0.5 text-xs bg-emerald-500/20 fi-text-success rounded-full">
                                    Tú
                                  </span>
                                </div>
                                <p className="fi-subtitle">
                                  {membership.especialidad || 'General'} • {membership.clinic_role}
                                </p>
                              </div>
                            </div>
                            <div className="text-right">
                              <span className="text-xs fi-text-success">{membership.email}</span>
                            </div>
                          </div>
                        )}

                        {/* Other doctors */}
                        {doctors
                          .filter((d) => d.auth0_user_id !== user?.sub)
                          .map((doctor) => (
                            <div
                              key={doctor.doctor_id}
                              className={`p-3 bg-slate-800/50 rounded-lg fi-flex-between ${
                                !doctor.is_active ? 'opacity-50' : ''
                              }`}
                            >
                              <div className="fi-flex-gap-md">
                                <div className="fi-icon-box-slate">
                                  <RoleIcon role={doctor.clinic_role} />
                                </div>
                                <div>
                                  <div className="fi-flex-gap">
                                    <p className="text-white font-medium">{doctor.display_name}</p>
                                    {doctor.is_linked && (
                                      <Check className="w-3 h-3 fi-text-green" />
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
                                  onClick={() => handleEditDoctorClick(doctor)}
                                  variant="ghost"
                                  size="sm"
                                  className="text-slate-400 hover:text-indigo-400 hover:bg-indigo-400/10"
                                  title="Editar horario"
                                  icon={Pencil}
                                />
                                <div className="text-right">
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
                          ))}
                        {doctors.length === 0 && !membership && !isSuperAdmin && (
                          <p className="text-slate-500 text-sm">No hay doctores registrados</p>
                        )}
                      </div>
                    </div>

                    {/* Appointments Section */}
                    <div>
                      <div className="fi-flex-between mb-3">
                        <h3 className="fi-title fi-flex-gap">
                          <Calendar className="w-5 h-5 text-indigo-400" />
                          Citas ({appointments.length})
                        </h3>
                      </div>
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {appointments.map((apt) => (
                          <div
                            key={apt.appointment_id}
                            className="p-3 bg-slate-800/50 rounded-lg"
                          >
                            <div className="fi-flex-between">
                              <div>
                                <p className="text-white text-sm">
                                  {new Date(apt.scheduled_at).toLocaleString('es-MX')}
                                </p>
                                <p className="text-slate-400 text-xs">{apt.reason || apt.appointment_type}</p>
                              </div>
                              <div className="text-right">
                                <div className="fi-flex-gap">
                                  <QrCode className="w-4 h-4 fi-text-green" />
                                  <span className="font-mono text-lg fi-text-green">
                                    {apt.checkin_code}
                                  </span>
                                </div>
                                <span className={`text-xs ${
                                  apt.status === 'scheduled' ? 'text-yellow-400' :
                                  apt.status === 'confirmed' ? 'fi-text-primary' :
                                  apt.status === 'checked_in' ? 'fi-text-green' :
                                  'text-slate-400'
                                }`}>
                                  {apt.status}
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                        {appointments.length === 0 && (
                          <p className="text-slate-500 text-sm">No hay citas registradas</p>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full py-24 text-slate-500">
                <Building2 className="w-16 h-16 mb-4 opacity-50" />
                <p>Selecciona una clínica para ver sus detalles</p>
              </div>
            )}
          </div>
        </div>

        {/* Create Clinic Modal */}
        {showCreateModal && (
          <CreateClinicModal
            onClose={() => setShowCreateModal(false)}
            onCreate={handleCreateClinic}
          />
        )}

        {/* Link to Clinic Modal */}
        {showLinkModal && selectedClinic && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-slate-900 rounded-lg border border-slate-700 p-6 w-full max-w-md">
              <div className="fi-flex-between mb-6">
                <h2 className="fi-title-xl">Vincularme a {selectedClinic.name}</h2>
                <button onClick={() => setShowLinkModal(false)} className="fi-btn-close">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <p className="text-slate-400 text-sm mb-4">
                Al vincularte a esta clínica, aparecerás como miembro del equipo y podrás gestionar citas y pacientes.
              </p>

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleLinkToClinic();
                }}
                className="space-y-4"
              >
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block fi-subtitle mb-1">Nombre *</label>
                    <Input
                      value={linkForm.nombre}
                      onChange={(e) => setLinkForm({ ...linkForm, nombre: e.target.value })}
                      placeholder="Tu nombre"
                      required
                      className="bg-slate-800 border-slate-700 text-white"
                    />
                  </div>
                  <div>
                    <label className="block fi-subtitle mb-1">Apellido *</label>
                    <Input
                      value={linkForm.apellido}
                      onChange={(e) => setLinkForm({ ...linkForm, apellido: e.target.value })}
                      placeholder="Tu apellido"
                      required
                      className="bg-slate-800 border-slate-700 text-white"
                    />
                  </div>
                </div>

                <div>
                  <label className="block fi-subtitle mb-1">Especialidad</label>
                  <Input
                    value={linkForm.especialidad}
                    onChange={(e) => setLinkForm({ ...linkForm, especialidad: e.target.value })}
                    placeholder="Ej: Medicina General, Cardiología"
                    className="bg-slate-800 border-slate-700 text-white"
                  />
                </div>

                <div>
                  <label className="block fi-subtitle mb-1">Rol en la clínica</label>
                  <Select value={linkForm.role} onValueChange={(val) => setLinkForm({ ...linkForm, role: val as ClinicRole })}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Seleccionar rol" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="OWNER">Propietario (Owner)</SelectItem>
                      <SelectItem value="ADMIN">Administrador</SelectItem>
                      <SelectItem value="DOCTOR">Doctor</SelectItem>
                      <SelectItem value="STAFF">Staff</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex gap-3 pt-4">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setShowLinkModal(false)}
                    className="flex-1"
                  >
                    Cancelar
                  </Button>
                  <Button
                    type="submit"
                    disabled={linkingToClinic || !linkForm.nombre || !linkForm.apellido}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                  >
                    {linkingToClinic ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <UserPlus className="w-4 h-4 mr-2" />
                    )}
                    Vincularme
                  </Button>
                </div>
              </form>
            </div>
          </div>
        )}

      {/* Edit Doctor Modal */}
      {showEditDoctorModal && editingDoctor && (
        <DoctorDetailModal
          doctor={editingDoctor}
          onClose={() => {
            setShowEditDoctorModal(false);
            setEditingDoctor(null);
          }}
          onSave={handleUpdateDoctor}
          mode="edit"
        />
      )}

      {/* Create Doctor Modal */}
      {showCreateDoctorModal && selectedClinic && (
        <CreateDoctorModal
          clinicId={selectedClinic.clinic_id}
          clinicName={selectedClinic.name}
          onClose={() => setShowCreateDoctorModal(false)}
          onCreate={(newDoctor) => {
            setDoctors((prev) => [...prev, newDoctor]);
            // Reload limits after adding doctor
            fetchDoctorLimits(selectedClinic.clinic_id).then(setDoctorLimits);
          }}
        />
      )}

    </AppTemplate>
  );
}

// =============================================================================
// CREATE CLINIC MODAL
// =============================================================================

function CreateClinicModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (data: ClinicCreate) => Promise<void>;
}) {
  const [formData, setFormData] = useState<ClinicCreate>({
    name: '',
    specialty: 'general',
    welcome_message: '',
    payments_enabled: false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError('El nombre es requerido');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onCreate(formData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear la clínica');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-900 rounded-lg border border-slate-700 p-6 w-full max-w-md">
        <div className="fi-flex-between mb-6">
          <h2 className="fi-title-xl">Nueva Clínica</h2>
          <button onClick={onClose} className="fi-btn-close">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block fi-subtitle mb-1">Nombre *</label>
            <Input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Nombre de la clínica"
            />
          </div>

          <div>
            <label className="block fi-subtitle mb-1">Especialidad</label>
            <Select value={formData.specialty} onValueChange={(val) => setFormData({ ...formData, specialty: val })}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Seleccionar especialidad" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="general">General</SelectItem>
                <SelectItem value="pediatria">Pediatría</SelectItem>
                <SelectItem value="cardiologia">Cardiología</SelectItem>
                <SelectItem value="dermatologia">Dermatología</SelectItem>
                <SelectItem value="ginecologia">Ginecología</SelectItem>
                <SelectItem value="oftalmologia">Oftalmología</SelectItem>
                <SelectItem value="traumatologia">Traumatología</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="block fi-subtitle mb-1">Mensaje de bienvenida</label>
            <textarea
              value={formData.welcome_message}
              onChange={(e) => setFormData({ ...formData, welcome_message: e.target.value })}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:border-indigo-500 focus:outline-none"
              rows={2}
              placeholder="¡Bienvenido a nuestra clínica!"
            />
          </div>

          <div className="fi-flex-gap-md">
            <input
              type="checkbox"
              id="payments"
              checked={formData.payments_enabled}
              onChange={(e) => setFormData({ ...formData, payments_enabled: e.target.checked })}
              className="w-4 h-4 text-indigo-500"
            />
            <label htmlFor="payments" className="fi-subtitle">
              Habilitar pagos (Stripe)
            </label>
          </div>

          {error && (
            <div className="p-3 bg-red-950/20 border border-red-800 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              onClick={onClose}
              variant="secondary"
              fullWidth
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              disabled={saving}
              variant="indigo"
              fullWidth
              loading={saving}
            >
              Crear Clínica
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
