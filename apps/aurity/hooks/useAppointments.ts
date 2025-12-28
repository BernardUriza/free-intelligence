
import { useState, useEffect, useCallback } from "react";
import {
  fetchClinicsAPI,
  fetchDoctorsAPI,
  fetchAppointmentsAPI,
  updateAppointmentAPI,
  createAppointmentAPI,
  Clinic,
} from "@/services/appointmentService";
import type { Appointment, Doctor } from "@/components/bryntum/utils/appointment-transform.utils";
import { toastError, toastSuccess } from "@/lib/swal";

export function useAppointments(initialDate: Date = new Date()) {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [selectedClinic, setSelectedClinic] = useState<string>("");
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [currentDate, setCurrentDate] = useState(initialDate);
  const [loading, setLoading] = useState(true);

  const fetchClinics = useCallback(async () => {
    setLoading(true);
    const clinicData = await fetchClinicsAPI();
    setClinics(clinicData);
    if (clinicData.length > 0) {
      setSelectedClinic(clinicData[0].clinic_id);
    } else {
      setLoading(false);
    }
  }, []);

  const fetchDoctors = useCallback(async (clinicId: string) => {
    const doctorData = await fetchDoctorsAPI(clinicId);
    setDoctors(doctorData);
  }, []);

  const fetchAppointments = useCallback(async (clinicId: string, date: Date) => {
    const appointmentData = await fetchAppointmentsAPI(clinicId, date);
    setAppointments(appointmentData);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchClinics();
  }, [fetchClinics]);

  useEffect(() => {
    if (selectedClinic) {
      setLoading(true);
      fetchDoctors(selectedClinic);
      fetchAppointments(selectedClinic, currentDate);
    }
  }, [selectedClinic, currentDate, fetchDoctors, fetchAppointments]);

  const updateAppointment = async (
    appointmentId: string,
    data: Partial<Appointment>
  ) => {
    if (!selectedClinic) return;
    try {
      const updated = await updateAppointmentAPI(selectedClinic, appointmentId, data);
      setAppointments((prev) =>
        prev.map((apt) =>
          apt.appointment_id === updated.appointment_id ? updated : apt
        )
      );
      toastSuccess("Cita actualizada correctamente");
    } catch (error) {
      console.error("Failed to update appointment:", error);
      toastError(error instanceof Error ? error.message : "Error al actualizar cita");
      // Revert UI
      fetchAppointments(selectedClinic, currentDate);
    }
  };

  const createAppointment = async (appointmentData: any) => {
    if (!selectedClinic) return;
    try {
      const newAppointment = await createAppointmentAPI(selectedClinic, appointmentData);
      setAppointments((prev) => [...prev, newAppointment]);
      toastSuccess("Cita creada correctamente");
      return newAppointment;
    } catch (error) {
      console.error("Failed to create appointment:", error);
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
    fetchAppointments,
    updateAppointment,
    createAppointment,
  };
}
