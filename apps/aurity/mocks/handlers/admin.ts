// @ts-nocheck - MSW handler types are development-only
import { http, HttpResponse } from 'msw';
import { catalogModels, catalogSourcesStatus, compatibility, runningModels, systemResources } from '@/mocks/fixtures/admin';
import { ROUTES } from '@/lib/api/routes';

export const adminHandlers = [
  http.get(`${ROUTES.adminCatalog}/models`, () => HttpResponse.json({ models: catalogModels })),
  http.get(`${ROUTES.adminCatalog}/sources/status`, () => HttpResponse.json(catalogSourcesStatus)),
  http.post(`${ROUTES.adminCatalog}/models/install`, async ({ request }) => {
    await request.json();
    return HttpResponse.json({ status: 'queued' });
  }),
  http.delete(`${ROUTES.adminCatalog}/models/:modelId`, () => HttpResponse.json({ success: true })),

  http.get(ROUTES.adminPersonas, () =>
    HttpResponse.json({
      personas: [
        { id: 'general_assistant', name: 'Asistente General', description: 'Soporte clínico general' },
        { id: 'soap_editor', name: 'Editor SOAP', description: 'Generación y edición de notas SOAP' },
      ],
    })
  ),
  http.get(`${ROUTES.adminPersonas}/:id`, ({ params }) =>
    HttpResponse.json({ id: params.id, name: 'Asistente', description: 'Persona mock' })
  ),
  http.post(ROUTES.adminPersonas, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ id: `persona-${Date.now()}`, ...body });
  }),
  http.put(`${ROUTES.adminPersonas}/:id`, async ({ params, request }) => {
    const body = await request.json();
    return HttpResponse.json({ id: params.id, ...body });
  }),
  http.post(`${ROUTES.adminPersonas}/:id/test`, () => HttpResponse.json({ status: 'ok' })),
  http.delete(`${ROUTES.adminPersonas}/:id`, () => HttpResponse.json({ success: true })),

  http.get(`${ROUTES.adminSystem}/resources`, () => HttpResponse.json(systemResources)),
  http.get(`${ROUTES.adminSystem}/ollama/running`, () => HttpResponse.json(runningModels)),
  http.get(`${ROUTES.adminSystem}/compatibility/:modelId`, () => HttpResponse.json(compatibility)),
  http.post(`${ROUTES.adminSystem}/ollama/unload/:modelName`, () => HttpResponse.json({ success: true })),
];
