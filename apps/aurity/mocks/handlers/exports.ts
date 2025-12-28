// @ts-nocheck - MSW handler types are development-only
import { http, HttpResponse } from 'msw';
import { exportJobs } from '@/mocks/fixtures/exports';

export const exportHandlers = [
  http.post('/api/exports', async ({ request }) => {
    const body = await request.json();
    const id = `export-${Date.now()}`;
    exportJobs[id] = { id, status: 'processing', ...body };
    return HttpResponse.json({ exportId: id });
  }),

  http.get('/api/exports/:exportId', ({ params }) => {
    const job = exportJobs[params.exportId as string] ?? { id: params.exportId, status: 'processing' };
    return HttpResponse.json(job);
  }),

  http.post('/api/exports/:exportId/verify', () => HttpResponse.json({ status: 'ready' })),
];
