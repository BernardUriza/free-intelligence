import { http, HttpResponse } from 'msw';

export const auditHandlers = [
  http.get('/api/audit/logs', () =>
    HttpResponse.json({
      logs: [
        { id: 'log-1', action: 'session_started', timestamp: new Date().toISOString(), user_id: 'user-1' },
      ],
      total: 1,
    })
  ),
  http.get('/api/audit/stats', () => HttpResponse.json({ total: 1, errors: 0 })),
  http.get('/api/audit/operations', () => HttpResponse.json([])),
];
