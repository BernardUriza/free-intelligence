"use client";

/**
 * Appointments Calendar Page - REFACTORED
 * Card: FI-CHECKIN-005 (Phase 2)
 *
 * Medical appointments scheduler using modular Bryntum architecture.
 * Reduced from 655 lines to ~150 lines using shared infrastructure.
 * 
 * Architecture:
 * - Reuses bryntum/ hooks, configs, and utils
 * - Appointment-specific configs (presets, features, columns)
 * - Separated UI components (Toolbar, StatusLegend, EmptyState)
 * - Clean separation of concerns
 */

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";
import { AppTemplate } from "@/components/layout/AppTemplate";
import { adminAppointmentsHeader } from "@/config/page-headers";
import { AppointmentsToolbar, StatusLegend, EmptyState, NewAppointmentModal, EditAppointmentModal } from "@/components/appointments";
import { ClinicCard, DoctorAvailabilityList } from "@/components/dashboard/QueueComponents";
import { APPOINTMENT_VIEW_PRESETS, type AppointmentViewMode } from "@/components/bryntum/config/appointment-presets.config";
import type { Appointment } from "@/components/bryntum/utils/appointment-transform.utils";
import type { BryntumSchedulerInstance } from "@/components/bryntum/types/scheduler.types";
import { useAppointments } from "@/hooks/useAppointments";

// Lazy load AppointmentsCalendar (defers Bryntum ~800KB)
const AppointmentsCalendar = dynamic(
  () => import("@/components/appointments/AppointmentsCalendar").then((mod) => ({
    default: mod.AppointmentsCalendar,
  })),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-cyan-500" />
      </div>
    ),
  }
);

export default function AppointmentsCalendarPage() {
  // State
  const {
    clinics,
    selectedClinic,
    setSelectedClinic,
    doctors,
    appointments,
    currentDate,
    setCurrentDate,
    loading,
    fetchAppointments,
    updateAppointment,
    createAppointment,
  } = useAppointments();

  const [viewMode, setViewMode] = useState<AppointmentViewMode>("day");
  const [isNewAppointmentModalOpen, setIsNewAppointmentModalOpen] = useState(false);
  const [isEditAppointmentModalOpen, setIsEditAppointmentModalOpen] = useState(false);
  const [selectedAppointment, setSelectedAppointment] = useState<Appointment | null>(null);
  const [prefilledData, setPrefilledData] = useState<{ date?: Date; doctorId?: string; endDate?: Date } | null>(null);

  // Scheduler instance & zoom state
  const [schedulerInstance, setSchedulerInstance] = useState<BryntumSchedulerInstance | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(10); // Default Bryntum zoom level

  const handleSchedulerReady = useCallback((instance: BryntumSchedulerInstance) => {
    setSchedulerInstance(instance);
    if (instance.zoomLevel !== undefined) {
      setZoomLevel(instance.zoomLevel);
    }
  }, []);

  const handleZoomIn = useCallback(() => {
    if (schedulerInstance?.zoomIn) {
      schedulerInstance.zoomIn();
      if (schedulerInstance.zoomLevel !== undefined) {
        setZoomLevel(schedulerInstance.zoomLevel);
      }
    }
  }, [schedulerInstance]);

  const handleZoomOut = useCallback(() => {
    if (schedulerInstance?.zoomOut) {
      schedulerInstance.zoomOut();
      if (schedulerInstance.zoomLevel !== undefined) {
        setZoomLevel(schedulerInstance.zoomLevel);
      }
    }
  }, [schedulerInstance]);

  // Horizontal scroll navigation (scroll by ~3 hours = 240px at tickWidth 80)
  const SCROLL_AMOUNT = 240;

  const handleScrollLeft = useCallback(() => {
    if (!schedulerInstance) return;
    const subgrid = document.querySelector('.b-grid-subgrid[data-region="normal"]');
    if (subgrid) {
      subgrid.scrollLeft = Math.max(0, subgrid.scrollLeft - SCROLL_AMOUNT);
    }
  }, [schedulerInstance]);

  const handleScrollRight = useCallback(() => {
    if (!schedulerInstance) return;
    const subgrid = document.querySelector('.b-grid-subgrid[data-region="normal"]');
    if (subgrid) {
      const maxScroll = subgrid.scrollWidth - subgrid.clientWidth;
      subgrid.scrollLeft = Math.min(maxScroll, subgrid.scrollLeft + SCROLL_AMOUNT);
    }
  }, [schedulerInstance]);

  // Navigation handlers
  function navigateDate(direction: "prev" | "next") {
    const newDate = new Date(currentDate);
    const viewConfig = APPOINTMENT_VIEW_PRESETS[viewMode];
    const delta = direction === "next" ? 1 : -1;

    switch (viewConfig.navigationUnit) {
      case "day":
        newDate.setDate(newDate.getDate() + delta);
        break;
      case "week":
        newDate.setDate(newDate.getDate() + delta * 7);
        break;
      case "month":
        newDate.setMonth(newDate.getMonth() + delta);
        break;
    }

    setCurrentDate(newDate);
  }

  function goToToday() {
    setCurrentDate(new Date());
  }

  function getDateDisplayText(): string {
    const viewConfig = APPOINTMENT_VIEW_PRESETS[viewMode];

    if (viewMode === "week") {
      const { start, end } = viewConfig.getDateRange(currentDate);
      const startStr = start.toLocaleDateString("es-MX", {
        day: "numeric",
        month: "short",
      });
      const endStr = end.toLocaleDateString("es-MX", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
      return `${startStr} - ${endStr}`;
    }

    return currentDate.toLocaleDateString("es-MX", viewConfig.dateFormat);
  }

  // Event handlers - API integration
  async function handleEventDrop(eventData: {
    appointment_id: string;
    scheduled_at: string;
    doctor_id: string;
  }) {
    await updateAppointment(eventData.appointment_id, {
      scheduled_at: eventData.scheduled_at,
      doctor_id: eventData.doctor_id,
    });
  }

  async function handleEventResize(eventData: {
    appointment_id: string;
    estimated_duration: number;
  }) {
    await updateAppointment(eventData.appointment_id, {
      estimated_duration: eventData.estimated_duration,
    });
  }

  async function handleEventEdit(eventData: Partial<Appointment>) {
    if (!eventData.appointment_id) return;
    await updateAppointment(eventData.appointment_id, eventData);
  }

  function handleNewAppointment() {
    setPrefilledData(null); // Reset prefilled data
    setIsNewAppointmentModalOpen(true);
  }

  function handleEventClick(appointment: Appointment) {
    setSelectedAppointment(appointment);
    setIsEditAppointmentModalOpen(true);
  }

  function handleScheduleClick(date: Date, doctorId: string, endDate?: Date | null) {
    // Pre-fill modal with clicked/dragged date range and doctor
    setPrefilledData({ date, doctorId, endDate: endDate ?? undefined });
    setIsNewAppointmentModalOpen(true);
  }

  async function handleCreateAppointment(appointmentData: Omit<Appointment, 'appointment_id'>) {
    try {
      await createAppointment(appointmentData);
      setIsNewAppointmentModalOpen(false);
    } catch {
      // Error is already handled in the hook
    }
  }

  // Loading state
  if (loading && !selectedClinic) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-12 w-12 animate-spin text-cyan-500" />
      </div>
    );
  }

  // Calculate appointments today for header
  const appointmentsToday = appointments.filter((apt) => {
    const aptDate = new Date(apt.scheduled_at);
    const today = new Date();
    return aptDate.toDateString() === today.toDateString();
  }).length;

  const headerConfig = adminAppointmentsHeader({ appointmentsToday });

  return (
    <>
      <AppTemplate
        headerConfig={headerConfig}
        backgroundGradient="none"
        padding="0"
        showWatermark={true}
        showGeometricBg={true}
      >
        {/* Toolbar + Scheduler Container */}
        <div className="px-6 pt-4">
          <AppointmentsToolbar
            clinics={clinics}
            selectedClinic={selectedClinic}
            onClinicChange={setSelectedClinic}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            onNavigateDate={navigateDate}
            onGoToToday={goToToday}
            onZoomIn={handleZoomIn}
            onZoomOut={handleZoomOut}
            zoomLevel={zoomLevel}
            maxZoomLevel={14}
            onScrollLeft={handleScrollLeft}
            onScrollRight={handleScrollRight}
            onRefresh={() => fetchAppointments(selectedClinic, currentDate)}
            onNewAppointment={handleNewAppointment}
            dateDisplayText={getDateDisplayText()}
          />
        </div>
        <StatusLegend />
        {/* Doctors & Clinic mini status bar */}
        <div className="px-6 pb-2 flex flex-col md:flex-row gap-3">
          {selectedClinic && (
            <ClinicCard
              clinic={{
                id: selectedClinic,
                name: clinics.find((c) => c.clinic_id === selectedClinic)?.name || 'Clínica',
              }}
            />
          )}
          {doctors.length > 0 && (
            <DoctorAvailabilityList
              doctors={doctors.map((d) => {
                // Type assertion: Doctor type doesn't have index signature, so we cast via unknown
                const doctor = d as unknown as Record<string, unknown>;
                return {
                  id: (doctor.doctor_id as string) || (doctor.id as string) || (doctor.name as string) || 'doctor',
                  name: (doctor.name as string) || (doctor.full_name as string) || (doctor.label as string) || 'Doctor',
                  specialty: doctor.specialty as string,
                  available: (doctor.is_available as boolean) ?? true,
                };
              })}
            />
          )}
        </div>

        {/* Scheduler Container */}
        <div className="p-6 relative">
          {doctors.length > 0 ? (
            <AppointmentsCalendar
              doctors={doctors}
              appointments={appointments}
              viewMode={viewMode}
              currentDate={currentDate}
              onEventDrop={handleEventDrop}
              onEventResize={handleEventResize}
              onEventEdit={handleEventEdit}
              onEventClick={handleEventClick}
              onScheduleClick={handleScheduleClick}
              onSchedulerReady={handleSchedulerReady}
            />
          ) : (
            !loading && <EmptyState />
          )}
        </div>
      </AppTemplate>

      {/* New Appointment Modal */}
      <NewAppointmentModal
        mode="create"
        isOpen={isNewAppointmentModalOpen}
        onClose={() => {
          setIsNewAppointmentModalOpen(false);
          setPrefilledData(null);
        }}
        onCancel={() => {
          setIsNewAppointmentModalOpen(false);
          setPrefilledData(null);
        }}
        onSubmit={async (data) => {
          await handleCreateAppointment({
            ...data,
            // Ensure scheduled_at is ISO string (form may return Date or string)
            scheduled_at: typeof data.scheduled_at === 'string'
              ? data.scheduled_at
              : (data.scheduled_at as unknown as Date).toISOString(),
            // Required fields not in form - use defaults
            clinic_id: selectedClinic,
            status: 'scheduled',
            checkin_code: '', // Generated by backend
          });
          setPrefilledData(null);
        }}
        doctors={doctors}
        prefilledData={prefilledData}
      />

      {/* Edit Appointment Modal */}
      <EditAppointmentModal
        mode="edit"
        isOpen={isEditAppointmentModalOpen}
        onClose={() => {
          setIsEditAppointmentModalOpen(false);
          setSelectedAppointment(null);
        }}
        onCancel={() => {
          setIsEditAppointmentModalOpen(false);
          setSelectedAppointment(null);
        }}
        onSubmit={async (payload) => {
          const aptId = payload.appointment_id || selectedAppointment?.appointment_id || '';
          if (!aptId) return;
          await handleEventEdit({
            appointment_id: aptId,
            ...payload,
          });
        }}
        initialData={selectedAppointment ? {
          appointment_id: selectedAppointment.appointment_id,
          patient_id: selectedAppointment.patient_id,
          doctor_id: selectedAppointment.doctor_id,
          scheduled_date: new Date(selectedAppointment.scheduled_at).toISOString().slice(0,10),
          scheduled_time: new Date(selectedAppointment.scheduled_at).toISOString().slice(11,16),
          // Cast to expected union type (API returns string)
          appointment_type: (selectedAppointment.appointment_type || 'FOLLOW_UP') as 'FIRST_TIME' | 'FOLLOW_UP' | 'PROCEDURE' | 'EMERGENCY' | 'TELEMEDICINE',
          estimated_duration: selectedAppointment.estimated_duration,
          reason: selectedAppointment.reason || '',
          notes: selectedAppointment.notes || ''
        } : undefined}
        doctors={doctors}
      />
    </>
  );
}
