// @ts-nocheck - MSW handler types are development-only
import { http, HttpResponse, ws } from 'msw';
import { checkinSession, waitingRoomState } from '@/mocks/fixtures/checkin';
import { ROUTES } from '@/lib/api/routes';

export const checkinHandlers = [
  http.post(`${ROUTES.checkin}/qr/generate`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      qr_url: `https://qr.mock/${body?.clinic_id ?? 'clinic-1'}`,
      expires_at: new Date(Date.now() + 3_600_000).toISOString(),
    });
  }),

  http.post(`${ROUTES.checkin}/session/start`, () => HttpResponse.json(checkinSession)),
  http.get(`${ROUTES.checkin}/session/:sessionId`, () => HttpResponse.json(checkinSession)),

  http.post(`${ROUTES.checkin}/identify/code`, () =>
    HttpResponse.json({ patient_id: 'patient-1', name: 'Paciente Demo' })
  ),
  http.post(`${ROUTES.checkin}/identify/curp`, () =>
    HttpResponse.json({ patient_id: 'patient-1', name: 'Paciente Demo' })
  ),
  http.post(`${ROUTES.checkin}/identify/name`, () =>
    HttpResponse.json({ patient_id: 'patient-1', name: 'Paciente Demo' })
  ),

  http.get(`${ROUTES.checkin}/actions/:appointmentId`, () =>
    HttpResponse.json([{ id: 'action-1', label: 'Confirmar datos', status: 'pending' }])
  ),
  http.post(`${ROUTES.checkin}/actions/:actionId/complete`, () => HttpResponse.json({ success: true })),
  http.post(`${ROUTES.checkin}/actions/:actionId/skip`, () => HttpResponse.json({ success: true })),

  http.post(`${ROUTES.checkin}/complete`, () => HttpResponse.json({ status: 'completed' })),
  http.get(`${ROUTES.checkin}/waiting-room/:clinicId`, () => HttpResponse.json(waitingRoomState)),

  // WebSocket handlers for both ws:// (dev) and wss:// (prod)
  ws.link('ws://*/api/checkin/waiting-room/:clinicId/ws', {
    onConnect(_, client) {
      client.send(waitingRoomState);
    },
  }),
  ws.link('wss://*/api/checkin/waiting-room/:clinicId/ws', {
    onConnect(_, client) {
      client.send(waitingRoomState);
    },
  }),
];
