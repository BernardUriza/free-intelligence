// @ts-nocheck - MSW handler types are development-only
import { http, HttpResponse } from 'msw';
import { catalogModels, catalogSourcesStatus, compatibility, runningModels, systemResources } from '@/mocks/fixtures/admin';

export const adminHandlers = [
  http.get('/api/admin/catalog/models', () => HttpResponse.json({ models: catalogModels })),
  http.get('/api/admin/catalog/sources/status', () => HttpResponse.json(catalogSourcesStatus)),
  http.post('/api/admin/catalog/models/install', async ({ request }) => {
    await request.json();
    return HttpResponse.json({ status: 'queued' });
  }),
  http.delete('/api/admin/catalog/models/:modelId', () => HttpResponse.json({ success: true })),

  http.get('/api/admin/personas', () =>
    HttpResponse.json({
      personas: [
        { id: 'general_assistant', name: 'Asistente General', description: 'Soporte clínico general' },
        { id: 'soap_editor', name: 'Editor SOAP', description: 'Generación y edición de notas SOAP' },
      ],
    })
  ),
  http.get('/api/admin/personas/:id', ({ params }) =>
    HttpResponse.json({ id: params.id, name: 'Asistente', description: 'Persona mock' })
  ),
  http.post('/api/admin/personas', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ id: `persona-${Date.now()}`, ...body });
  }),
  http.put('/api/admin/personas/:id', async ({ params, request }) => {
    const body = await request.json();
    return HttpResponse.json({ id: params.id, ...body });
  }),
  http.post('/api/admin/personas/:id/test', () => HttpResponse.json({ status: 'ok' })),
  http.delete('/api/admin/personas/:id', () => HttpResponse.json({ success: true })),

  http.get('/api/admin/system/resources', () => HttpResponse.json(systemResources)),
  http.get('/api/admin/system/ollama/running', () => HttpResponse.json(runningModels)),
  http.get('/api/admin/system/compatibility/:modelId', () => HttpResponse.json(compatibility)),
  http.post('/api/admin/system/ollama/unload/:modelName', () => HttpResponse.json({ success: true })),
];
