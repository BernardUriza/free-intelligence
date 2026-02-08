// @ts-nocheck - MSW handler types are development-only
import { http, HttpResponse } from 'msw';
import { appointments, clinics, doctors, membership } from '@/mocks/fixtures/clinics';
import { ROUTES } from '@/lib/api/routes';

export const clinicHandlers = [
  http.get(ROUTES.clinics, () => HttpResponse.json(clinics)),
  http.get(`${ROUTES.clinics}/:clinicId`, ({ params }) => {
    const clinic = clinics.find((c) => c.id === params.clinicId) ?? clinics[0];
    return HttpResponse.json(clinic);
  }),
  http.post(ROUTES.clinics, async ({ request }) => {
    const body = await request.json();
    const created = { id: `clinic-${Date.now()}`, ...body };
    clinics.push(created);
    return HttpResponse.json(created);
  }),
  http.patch(`${ROUTES.clinics}/:clinicId`, async ({ params, request }) => {
    const body = await request.json();
    const idx = clinics.findIndex((c) => c.id === params.clinicId);
    if (idx >= 0) clinics[idx] = { ...clinics[idx], ...body };
    return HttpResponse.json(clinics[idx] ?? body);
  }),
  http.delete(`${ROUTES.clinics}/:clinicId`, () => HttpResponse.json({ success: true })),

  http.get(`${ROUTES.clinics}/:clinicId/doctors`, () => HttpResponse.json(doctors)),
  http.post(`${ROUTES.clinics}/:clinicId/doctors`, async ({ request }) => {
    const body = await request.json();
    const created = { id: `doc-${Date.now()}`, ...body };
    doctors.push(created);
    return HttpResponse.json(created);
  }),
  http.patch(`${ROUTES.clinics}/:clinicId/doctors/:doctorId`, async ({ params, request }) => {
    const body = await request.json();
    const idx = doctors.findIndex((d) => d.id === params.doctorId);
    if (idx >= 0) doctors[idx] = { ...doctors[idx], ...body };
    return HttpResponse.json(doctors[idx] ?? body);
  }),
  http.delete(`${ROUTES.clinics}/:clinicId/doctors/:doctorId`, () => HttpResponse.json({ success: true })),

  http.get(`${ROUTES.clinics}/:clinicId/appointments`, () => HttpResponse.json(appointments)),
  http.post(`${ROUTES.clinics}/:clinicId/appointments`, async ({ params, request }) => {
    const body = await request.json();
    const created = { id: `appt-${Date.now()}`, clinic_id: params.clinicId, ...body };
    appointments.push(created);
    return HttpResponse.json(created);
  }),
  http.get(`${ROUTES.clinics}/:clinicId/appointments/:id`, ({ params }) => {
    const appt = appointments.find((a) => a.id === params.id) ?? appointments[0];
    return HttpResponse.json(appt);
  }),
  http.patch(`${ROUTES.clinics}/:clinicId/appointments/:id`, async ({ params, request }) => {
    const body = await request.json();
    const idx = appointments.findIndex((a) => a.id === params.id);
    if (idx >= 0) appointments[idx] = { ...appointments[idx], ...body };
    return HttpResponse.json(appointments[idx] ?? body);
  }),

  http.get(`${ROUTES.clinicUsers}/clinic-membership`, () => HttpResponse.json(membership)),
  http.post(`${ROUTES.clinicUsers}/link-to-clinic`, () => HttpResponse.json({ success: true })),
  http.delete(`${ROUTES.clinicUsers}/unlink-from-clinic`, () => HttpResponse.json({ success: true })),
];
