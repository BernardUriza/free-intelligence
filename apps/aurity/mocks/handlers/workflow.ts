// @ts-nocheck - MSW handler types are development-only
import { http, HttpResponse } from 'msw';
import type { MedicalOrder } from '@aurity-standalone/api-client/medical-workflow';
import { ROUTES } from '@/lib/api/routes';
import {
  checkpointResponse,
  diarizationJobId,
  diarizationSegments,
  endSessionResponse,
  kpiSummary,
  medicalOrders,
  sessionId,
  sessionMonitorText,
  soapNote,
  streamChunkResponse,
  timelineEvents,
  timelineSession,
  transcriptionSources,
} from '@/mocks/fixtures/workflow';

let orders = [...medicalOrders];

export const workflowHandlers = [
  http.post(ROUTES.stream, async ({ request }) => {
    const form = await request.formData();
    const chunkNumber = Number(form.get('chunk_number') ?? 0);
    return HttpResponse.json(streamChunkResponse(chunkNumber));
  }),

  http.post(`${ROUTES.medicalAi}/sessions/:id/checkpoint`, () => {
    return HttpResponse.json(checkpointResponse);
  }),

  http.post(ROUTES.endSession, async ({ request }) => {
    const form = await request.formData();
    const incomingSession = form.get('session_id')?.toString() || sessionId;
    return HttpResponse.json({ ...endSessionResponse, session_id: incomingSession });
  }),

  http.post(`${ROUTES.medicalAi}/sessions/:id/diarization`, () => {
    return HttpResponse.json({ job_id: diarizationJobId });
  }),

  http.get(`${ROUTES.medicalAi}/diarization/jobs/:jobId`, ({ params }) => {
    const { jobId } = params;
    const progress = jobId === diarizationJobId ? 100 : 50;
    return HttpResponse.json({ status: 'completed', progress });
  }),

  http.get(`${ROUTES.medicalAi}/sessions/:id/diarization/segments`, () => {
    return HttpResponse.json({
      session_id: sessionId,
      segments: diarizationSegments,
      segment_count: diarizationSegments.length,
      provider: 'mock-provider',
      completed_at: new Date().toISOString(),
    });
  }),

  http.post(`${ROUTES.medicalAi}/sessions/:id/soap`, () => {
    return HttpResponse.json({ job_id: 'soap-job-1' });
  }),

  http.get(`${ROUTES.medicalAi}/sessions/:id/soap`, () => HttpResponse.json(soapNote)),

  http.put(`${ROUTES.medicalAi}/sessions/:id/soap`, async ({ request }) => {
    const body = await request.json();
    // Accept payload; respond with created orders count
    const ordersCreated = body?.soap_note?.plan?.medications?.length ? 1 : 0;
    return HttpResponse.json({ orders_created: ordersCreated });
  }),

  http.get(`${ROUTES.medicalAi}/sessions/:id/orders`, () => HttpResponse.json(orders)),

  http.post(`${ROUTES.medicalAi}/sessions/:id/orders`, async ({ request }) => {
    const body = (await request.json()) as Partial<MedicalOrder> & { description: string };
    const newOrder = {
      id: `order-${Date.now()}`,
      type: body.type ?? 'medication',
      description: body.description,
      details: body.details,
      source: 'manual',
      created_at: new Date().toISOString(),
    } satisfies MedicalOrder;
    orders = [...orders, newOrder];
    return HttpResponse.json(newOrder.id);
  }),

  http.put(`${ROUTES.medicalAi}/sessions/:id/orders/:orderId`, async ({ params, request }) => {
    const { orderId } = params;
    const body = await request.json();
    orders = orders.map((o) => (o.id === orderId ? { ...o, ...body } : o));
    return HttpResponse.json({ success: true });
  }),

  http.delete(`${ROUTES.medicalAi}/sessions/:id/orders/:orderId`, ({ params }) => {
    const { orderId } = params;
    orders = orders.filter((o) => o.id !== orderId);
    return HttpResponse.json({ success: true });
  }),

  http.get(`${ROUTES.medicalAi}/sessions/:id/transcription-sources`, () =>
    HttpResponse.json(transcriptionSources)
  ),

  http.get(`${ROUTES.medicalAi}/sessions/:id/chunks`, () =>
    HttpResponse.json(transcriptionSources.transcription_per_chunks)
  ),

  http.get(`${ROUTES.medicalAi}/sessions/:id/monitor`, () =>
    new HttpResponse(sessionMonitorText, {
      headers: { 'Content-Type': 'text/plain; charset=utf-8' },
    })
  ),

  http.get(`${ROUTES.medicalAi}/sessions/:id`, () => HttpResponse.json(timelineSession)),

  http.get(ROUTES.sessions, () => HttpResponse.json({ sessions: [timelineSession], total: 1 })),

  http.get(`${ROUTES.timeline}/sessions`, () =>
    HttpResponse.json({ sessions: [timelineSession], total: 1 })
  ),

  http.get(`${ROUTES.timeline}/events`, () => HttpResponse.json({ events: timelineEvents })),

  http.get(`${ROUTES.timeline}/stats`, () =>
    HttpResponse.json({ total_sessions: 1, avg_duration_minutes: 18 })
  ),

  http.get(`${ROUTES.timeline}/memory`, () =>
    HttpResponse.json({
      session_id: timelineSession.session_id,
      summary: 'Memoria de la sesión mock',
      recent_events: timelineEvents,
    })
  ),

  http.get(ROUTES.health, () => HttpResponse.json({ status: 'healthy' })),

  http.get(ROUTES.kpis, () => HttpResponse.json(kpiSummary)),

  http.get(`${ROUTES.clinicMedia}/list`, () =>
    HttpResponse.json({ items: [{ id: 'media-1', title: 'Pantalla demo', active: true }] })
  ),

  http.get(`${ROUTES.system}/disk-usage`, () =>
    HttpResponse.json({ used_gb: 120, total_gb: 500 })
  ),

  http.post(`${ROUTES.system}/clear-memory`, () =>
    HttpResponse.json({ status: 'ok', cleared_gb: 1.5 })
  ),
];
