export const clinics = [
  {
    id: 'clinic-1',
    name: 'Clínica Demo Norte',
    address: 'Av. Demo 123',
    active: true,
  },
];

export const doctors = [
  {
    id: 'doc-1',
    name: 'Dra. Demo',
    specialty: 'Medicina Familiar',
    active: true,
  },
];

export const appointments = [
  {
    id: 'appt-1',
    clinic_id: 'clinic-1',
    doctor_id: 'doc-1',
    patient_name: 'Paciente Demo',
    scheduled_start: new Date(Date.now() + 3_600_000).toISOString(),
    status: 'scheduled',
  },
];

export const membership = {
  clinic_id: 'clinic-1',
  role: 'member',
};
