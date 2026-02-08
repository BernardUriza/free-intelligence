// @ts-nocheck - MSW handler types are development-only
import { http, HttpResponse } from 'msw';
import { appointments, clinics, doctors, membership } from '@/mocks/fixtures/clinics';

export const clinicHandlers = [
  http.get('/api/aurity/clinic/clinics', () => HttpResponse.json(clinics)),
  http.get('/api/aurity/clinic/clinics/:clinicId', ({ params }) => {
    const clinic = clinics.find((c) => c.id === params.clinicId) ?? clinics[0];
    return HttpResponse.json(clinic);
  }),
  http.post('/api/aurity/clinic/clinics', async ({ request }) => {
    const body = await request.json();
    const created = { id: `clinic-${Date.now()}`, ...body };
    clinics.push(created);
    return HttpResponse.json(created);
  }),
  http.patch('/api/aurity/clinic/clinics/:clinicId', async ({ params, request }) => {
    const body = await request.json();
    const idx = clinics.findIndex((c) => c.id === params.clinicId);
    if (idx >= 0) clinics[idx] = { ...clinics[idx], ...body };
    return HttpResponse.json(clinics[idx] ?? body);
  }),
  http.delete('/api/aurity/clinic/clinics/:clinicId', () => HttpResponse.json({ success: true })),

  http.get('/api/aurity/clinic/clinics/:clinicId/doctors', () => HttpResponse.json(doctors)),
  http.post('/api/aurity/clinic/clinics/:clinicId/doctors', async ({ request }) => {
    const body = await request.json();
    const created = { id: `doc-${Date.now()}`, ...body };
    doctors.push(created);
    return HttpResponse.json(created);
  }),
  http.patch('/api/aurity/clinic/clinics/:clinicId/doctors/:doctorId', async ({ params, request }) => {
    const body = await request.json();
    const idx = doctors.findIndex((d) => d.id === params.doctorId);
    if (idx >= 0) doctors[idx] = { ...doctors[idx], ...body };
    return HttpResponse.json(doctors[idx] ?? body);
  }),
  http.delete('/api/aurity/clinic/clinics/:clinicId/doctors/:doctorId', () => HttpResponse.json({ success: true })),

  http.get('/api/aurity/clinic/clinics/:clinicId/appointments', () => HttpResponse.json(appointments)),
  http.post('/api/aurity/clinic/clinics/:clinicId/appointments', async ({ params, request }) => {
    const body = await request.json();
    const created = { id: `appt-${Date.now()}`, clinic_id: params.clinicId, ...body };
    appointments.push(created);
    return HttpResponse.json(created);
  }),
  http.get('/api/aurity/clinic/clinics/:clinicId/appointments/:id', ({ params }) => {
    const appt = appointments.find((a) => a.id === params.id) ?? appointments[0];
    return HttpResponse.json(appt);
  }),
  http.patch('/api/aurity/clinic/clinics/:clinicId/appointments/:id', async ({ params, request }) => {
    const body = await request.json();
    const idx = appointments.findIndex((a) => a.id === params.id);
    if (idx >= 0) appointments[idx] = { ...appointments[idx], ...body };
    return HttpResponse.json(appointments[idx] ?? body);
  }),

  http.get('/api/aurity/clinic/users/me/clinic-membership', () => HttpResponse.json(membership)),
  http.post('/api/aurity/clinic/users/me/link-to-clinic', () => HttpResponse.json({ success: true })),
  http.delete('/api/aurity/clinic/users/me/unlink-from-clinic', () => HttpResponse.json({ success: true })),
];
