
import { useState, useEffect, useCallback } from "react";
import {
  fetchClinics,
  fetchDoctors,
  fetchAppointments as fetchAppointmentsApi,
  updateAppointment as updateAppointmentApi,
  createAppointment as createAppointmentApi,
  type Clinic,
} from "@/lib/api/clinics";
import type { Appointment, Doctor } from "@/components/bryntum/utils/appointment-transform.utils";
import { toastError, toastSuccess } from "@/lib/swal";
import { createLogger } from "@/lib/internal/logger";

const log = createLogger("Appointments");

export function useAppointments(initialDate: Date = new Date()) {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [selectedClinic, setSelectedClinic] = useState<string>("");
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [currentDate, setCurrentDate] = useState(initialDate);
  const [loading, setLoading] = useState(true);

  const loadClinics = useCallback(async () => {
    setLoading(true);
    const clinicData = await fetchClinics();
    setClinics(clinicData);
    if (clinicData.length > 0) {
      setSelectedClinic(clinicData[0].clinic_id);
    } else {
      setLoading(false);
    }
  }, []);

  const loadDoctors = useCallback(async (clinicId: string) => {
    const doctorData = await fetchDoctors(clinicId);
    setDoctors(doctorData);
  }, []);

  const loadAppointments = useCallback(async (clinicId: string, date: Date) => {
    const dateStr = date.toISOString().split("T")[0];
    const appointmentData = await fetchAppointmentsApi(clinicId, { date: dateStr });
    setAppointments(appointmentData as Appointment[]);
    setLoading(false);
  }, []);

  useEffect(() => {
    loadClinics();
  }, [loadClinics]);

  useEffect(() => {
    if (selectedClinic) {
      setLoading(true);
      loadDoctors(selectedClinic);
      loadAppointments(selectedClinic, currentDate);
    }
  }, [selectedClinic, currentDate, loadDoctors, loadAppointments]);

  const updateAppointment = async (
    appointmentId: string,
    data: Partial<Appointment>
  ) => {
    if (!selectedClinic) return;
    try {
      const updated = await updateAppointmentApi(selectedClinic, appointmentId, data);
      setAppointments((prev) =>
        prev.map((apt) =>
          apt.appointment_id === updated.appointment_id ? updated : apt
        )
      );
      toastSuccess("Cita actualizada correctamente");
    } catch (error) {
      log.error("Failed to update appointment", { error: String(error) });
      toastError(error instanceof Error ? error.message : "Error al actualizar cita");
      // Revert UI
      loadAppointments(selectedClinic, currentDate);
    }
  };

  const createAppointment = async (appointmentData: any) => {
    if (!selectedClinic) return;
    try {
      const newAppointment = await createAppointmentApi(selectedClinic, appointmentData);
      setAppointments((prev) => [...prev, newAppointment]);
      toastSuccess("Cita creada correctamente");
      return newAppointment;
    } catch (error) {
      log.error("Failed to create appointment", { error: String(error) });
      toastError(error instanceof Error ? error.message : "Error al crear cita");
      throw error;
    }
  };

  return {
    clinics,
    selectedClinic,
    setSelectedClinic,
    doctors,
    appointments,
    setAppointments,
    currentDate,
    setCurrentDate,
    loading,
    fetchAppointments: loadAppointments,
    updateAppointment,
    createAppointment,
  };
}
