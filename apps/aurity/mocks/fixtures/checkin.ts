export const checkinSession = {
  session_id: 'checkin-session-1',
  status: 'pending',
};

export const waitingRoomState = {
  clinic_id: 'clinic-1',
  queue: [
    { appointment_id: 'appt-1', patient_name: 'Paciente Demo', status: 'waiting' },
    { appointment_id: 'appt-2', patient_name: 'Paciente 2', status: 'in_progress' },
  ],
  estimated_wait_minutes: 12,
};
