// @ts-nocheck - MSW handler types are development-only
import { http, HttpResponse } from 'msw';
import { exportJobs } from '@/mocks/fixtures/exports';
import { ROUTES } from '@/lib/api/routes';

export const exportHandlers = [
  http.post(ROUTES.exports, async ({ request }) => {
    const body = await request.json();
    const id = `export-${Date.now()}`;
    exportJobs[id] = { id, status: 'processing', ...body };
    return HttpResponse.json({ exportId: id });
  }),

  http.get(`${ROUTES.exports}/:exportId`, ({ params }) => {
    const job = exportJobs[params.exportId as string] ?? { id: params.exportId, status: 'processing' };
    return HttpResponse.json(job);
  }),

  http.post(`${ROUTES.exports}/:exportId/verify`, () => HttpResponse.json({ status: 'ready' })),
];
