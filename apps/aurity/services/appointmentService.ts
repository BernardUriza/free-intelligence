
import { toastError } from "@/lib/swal";
import type { Appointment, Doctor } from "@/components/bryntum/utils/appointment-transform.utils";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:7001";

export interface Clinic {
  clinic_id: string;
  name: string;
}

export async function fetchClinicsAPI(): Promise<Clinic[]> {
  try {
    const res = await fetch(`${API_BASE}/api/clinics`);
    if (!res.ok) throw new Error("Failed to fetch clinics");
    const data = await res.json();
    return data.clinics || [];
  } catch (error) {
    console.error("Failed to fetch clinics:", error);
    toastError("Failed to fetch clinics");
    return [];
  }
}

export async function fetchDoctorsAPI(clinicId: string): Promise<Doctor[]> {
  try {
    const res = await fetch(`${API_BASE}/api/clinics/${clinicId}/doctors`);
    if (!res.ok) throw new Error("Failed to fetch doctors");
    const data = await res.json();
    return data.doctors || [];
  } catch (error) {
    console.error("Failed to fetch doctors:", error);
    toastError("Failed to fetch doctors");
    return [];
  }
}

export async function fetchAppointmentsAPI(clinicId: string, date: Date): Promise<Appointment[]> {
  try {
    const dateStr = date.toISOString().split("T")[0];
    const res = await fetch(
      `${API_BASE}/api/clinics/${clinicId}/appointments?date=${dateStr}`
    );
    if (!res.ok) throw new Error("Failed to fetch appointments");
    const data = await res.json();
    return data.appointments || [];
  } catch (error) {
    console.error("Failed to fetch appointments:", error);
    toastError("Failed to fetch appointments");
    return [];
  }
}

export async function updateAppointmentAPI(
  clinicId: string,
  appointmentId: string,
  data: Partial<Appointment>
): Promise<Appointment> {
  const res = await fetch(
    `${API_BASE}/api/clinics/${clinicId}/appointments/${appointmentId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }
  );

  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || "Failed to update appointment");
  }
  return res.json();
}

export async function createAppointmentAPI(
  clinicId: string,
  appointmentData: any
): Promise<Appointment> {
  // Support both ISO string and Date for scheduled_at
  const scheduledAt = (() => {
    const v = appointmentData.scheduled_at;
    if (!v) return undefined;
    if (typeof v === 'string') return v;
    try { return v.toISOString(); } catch { return undefined; }
  })();

  const payload = { ...appointmentData, scheduled_at: scheduledAt };
  const res = await fetch(`${API_BASE}/api/clinics/${clinicId}/appointments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    // Parse FastAPI error response for clearer messages
    let message = "Failed to create appointment";
    try {
      const err = await res.json();
      if (typeof err === 'string') message = err;
      else if (err?.detail) {
        if (Array.isArray(err.detail)) {
          // Pydantic validation errors
          const first = err.detail[0];
          const loc = Array.isArray(first?.loc) ? first.loc.join('.') : '';
          const msg = first?.msg || first?.message || String(first || 'Validation error');
          message = loc ? `${loc}: ${msg}` : msg;
        } else {
          message = err.detail;
        }
      }
    } catch {
      // ignore parsing error
    }
    throw new Error(message);
  }
  return res.json();
}
