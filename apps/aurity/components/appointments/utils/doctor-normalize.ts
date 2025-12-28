// Utility to normalize inbound doctor objects to the expected Doctor shape
import type { Doctor } from '@/components/bryntum/utils/appointment-transform.utils';

export type InboundDoctor = {
  doctor_id: string;
  display_name: string;
  especialidad: string;
  nombre?: string;
  apellido?: string;
  avg_consultation_minutes?: number;
};

export function normalizeDoctors(doctors: InboundDoctor[]): Doctor[] {
  return doctors.map((d) => {
    const parts = d.display_name?.trim()?.split(/\s+/) ?? [];
    const nombre = d.nombre ?? (parts[0] ?? d.display_name);
    const apellido = d.apellido ?? (parts.length > 1 ? parts.slice(1).join(' ') : '');
    return {
      doctor_id: d.doctor_id,
      display_name: d.display_name,
      nombre,
      apellido,
      especialidad: d.especialidad,
      avg_consultation_minutes: d.avg_consultation_minutes ?? 30,
    } as Doctor;
  });
}
