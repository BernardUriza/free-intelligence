import { http, HttpResponse } from 'msw';
import { ROUTES } from '@/lib/api/routes';

export const auditHandlers = [
  http.get(`${ROUTES.audit}/logs`, () =>
    HttpResponse.json({
      logs: [
        { id: 'log-1', action: 'session_started', timestamp: new Date().toISOString(), user_id: 'user-1' },
      ],
      total: 1,
    })
  ),
  http.get(`${ROUTES.audit}/stats`, () => HttpResponse.json({ total: 1, errors: 0 })),
  http.get(`${ROUTES.audit}/operations`, () => HttpResponse.json([])),
];
