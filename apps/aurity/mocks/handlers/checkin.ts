// @ts-nocheck - MSW handler types are development-only
import { http, HttpResponse, ws } from 'msw';
import { checkinSession, waitingRoomState } from '@/mocks/fixtures/checkin';

export const checkinHandlers = [
  http.post('/api/checkin/qr/generate', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      qr_url: `https://qr.mock/${body?.clinic_id ?? 'clinic-1'}`,
      expires_at: new Date(Date.now() + 3_600_000).toISOString(),
    });
  }),

  http.post('/api/checkin/session/start', () => HttpResponse.json(checkinSession)),
  http.get('/api/checkin/session/:sessionId', () => HttpResponse.json(checkinSession)),

  http.post('/api/checkin/identify/code', () =>
    HttpResponse.json({ patient_id: 'patient-1', name: 'Paciente Demo' })
  ),
  http.post('/api/checkin/identify/curp', () =>
    HttpResponse.json({ patient_id: 'patient-1', name: 'Paciente Demo' })
  ),
  http.post('/api/checkin/identify/name', () =>
    HttpResponse.json({ patient_id: 'patient-1', name: 'Paciente Demo' })
  ),

  http.get('/api/checkin/actions/:appointmentId', () =>
    HttpResponse.json([{ id: 'action-1', label: 'Confirmar datos', status: 'pending' }])
  ),
  http.post('/api/checkin/actions/:actionId/complete', () => HttpResponse.json({ success: true })),
  http.post('/api/checkin/actions/:actionId/skip', () => HttpResponse.json({ success: true })),

  http.post('/api/checkin/complete', () => HttpResponse.json({ status: 'completed' })),
  http.get('/api/checkin/waiting-room/:clinicId', () => HttpResponse.json(waitingRoomState)),

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
