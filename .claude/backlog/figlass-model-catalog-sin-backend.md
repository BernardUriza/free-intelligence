# FIGLASS-MODEL-CATALOG-BACKEND-1 — `fi-glass/model-catalog` no tiene backend vivo ni consumidor

Status: **Proposed**
Proposed: 2026-10-28 by Claude (hallazgo #2 del /cruel-critic de #611)

## What it is

`fi-glass/model-catalog` (registro de LLMs, catálogo Ollama/HF/GPT4All con descarga, recursos del
sistema) salió de aurity en #611. La UI es real y está probada, pero sólo contra un `ModelCatalogStore`
falso:

- El único servidor que contestaba sus rutas (`/admin/catalog`, `/admin/models`) es
  `backend/infrastructure/model_catalog/api/public/catalog_admin.py`, dentro de `backend/`, que es
  código muerto: no se despliega.
- aurity, el único consumidor (`apps/aurity/services/model-catalog.ts`), no tiene infraestructura
  desde julio de 2026.
- og118 no lo monta: sus motores son AIRE (`ELEMENT_ENGINE_OPTIONS`), no modelos locales.

Mientras siga así, nada demuestra que la forma del store coincida con un servidor real.
Ver [[both-ends-of-the-data-path]].

## Canonical path to reuse (Art. 6)

- El contrato ya existe: `ModelCatalogStore` en `apps/packages/fi-glass/src/model-catalog/types.ts`.
  Un backend nuevo lo implementa; la UI no se toca.
- El adaptador HTTP de referencia es `apps/aurity/services/model-catalog.ts` +
  `apps/aurity/lib/api/catalog.ts` (`installModelWithProgress` con SSE).
- Si revive en fi-runner/og118-api, la lógica de `catalog_admin.py` se mueve allá y `backend/` pierde
  ese módulo en el mismo PR ([[migrations-end-with-deletion]]).

## The decision that's the owner's

Lo decide Bernard:

1. Darle un consumidor vivo. Por ejemplo, og118 con modelos locales vía Ollama en el droplet de AIRE,
   lo que gasta CPU y RAM del droplet.
2. Revivir el endpoint en un servicio desplegado, que cuesta infraestructura.
3. Dejarlo como forma canónica sin backend, igual que aurity: se lee y no se ejecuta.

## Status / next step

Sin decisión. Mientras tanto, el recibo de que la UI funciona son los tests con store falso
(`ModelCatalog.test.tsx`) y la medición móvil de #611. El siguiente paso es que Bernard elija 1, 2 o 3.
