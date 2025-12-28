import { http, HttpResponse } from 'msw';

export const miscHandlers = [
  http.get('/api/policy', () =>
    HttpResponse.json({
      version: 'mock-1.0',
      summary: 'Política de privacidad mock para desarrollo sin backend.',
    })
  ),
];
