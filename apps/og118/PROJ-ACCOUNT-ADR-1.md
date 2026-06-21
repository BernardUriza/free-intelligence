# PROJ-ACCOUNT-ADR-1 — Modelo de cuenta y ownership de corpus para Projects

**Status:** Proposed — decisión de Bernard
**Fecha:** 2026-06-21
**Autor:** Claude Code (vía exchange-coagent; spec del coagent AURITY)
**Scope:** read-only / ADR. Cero código, cero cambios de auth/endpoints/fi-glass/voz/Gate 4.
**Decide:** qué cuenta posee qué project y qué `corpus_id` — el modelo de privacidad que hoy bloquea cerrar el canary Projects.

---

## 1. Inventario actual (estado REAL mergeado — verificado en código)

| Pieza | Dónde vive | Estado |
|---|---|---|
| Projects sidebar | `web/lib/useOg118Projects.ts` (localStorage) | Mergeado (#258) |
| Project upload | `server/app.py:335` `POST /projects/{project_id}/upload` | Mergeado (#257) |
| Corpus binding per turn | `server/runner.py` + `fi_runner.active_corpus_binding` | Mergeado (#256) |
| `rag_store` en el Runner | `server/runner.py:49` `capabilities=[..., "rag_store"]` | Mergeado (#255/#248) |
| Client-sent history | fi-runner `sanitize_history` + `run_stream(history=)` | Mergeado (#260) |
| Bearer actual | `server/app.py:61` `OG118_ACCESS_TOKEN` + `require_access` (hmac) | Vigente (speed-bump) |
| Gate 3 (auth real) | — | Pendiente |

### Campos que existen HOY

- **`project_id`** — generado en el **cliente** con `crypto.randomUUID()` (`useOg118Projects.ts:46`). Persistido en `localStorage` (`PROJECTS_KEY`, `ACTIVE_KEY`).
- **`corpus_id`** — **NO es un campo aparte**: `corpus_id == project_id`, 1:1 (`app.py:370` devuelve `{"corpus_id": project_id, ...}`; el comentario en `useOg118Projects.ts:17` lo confirma: "Also the corpus_id").
- **`doc_id`** — generado en el upload, dentro del corpus.
- **`owner` / `account`** — **NO EXISTE** en ningún lado (ni server ni cliente). El modelo de project es `{ id, name, createdAt }`, nada más.

### El hueco concreto (la razón de este ADR)

Hoy el **cliente decide arbitrariamente el `corpus_id`**: genera un UUID local y lo manda como path param a `POST /projects/{id}/upload` y como `context.corpus_id` por turno. El backend lo usa tal cual, sin validar pertenencia. No hay create/list/delete de projects server-side — el server solo ve un `project_id` cuando llega un upload o un turno. **Esto es exactamente lo que la invariante de privacidad debe prohibir.**

---

## 2. Modelo recomendado

**`account → projects → corpus`, con `corpus_id` por proyecto (per-project).**

NO corpus global por cuenta. Razones:

- privacidad más clara (un proyecto = un corpus aislado);
- listas escolares separadas por proyecto (negocio de la mamá);
- pricing separable por proyecto;
- menos riesgo de mezclar documentos;
- borrar/exportar un proyecto es atómico;
- buen fit con el caso real de la papelería.

Cardinalidad: `account 1—N project`, `project 1—1 corpus`. (El `corpus_id == project_id` actual se conserva como relación 1:1, pero el `project_id` pasa a ser **resuelto/validado server-side**, no fabricado por el cliente.)

---

## 3. Invariantes de privacidad (reglas duras)

1. Cada project tiene **exactamente un** `corpus_id` activo.
2. El `corpus_id` lo genera **backend o runtime controlado**, nunca el cliente.
3. El cliente **nunca** decide arbitrariamente un `corpus_id`.
4. Todo upload se vincula a un `project_id`.
5. `project_id` debe **resolver a `corpus_id` server-side** (no confiar en el path crudo).
6. Post-Gate-3: todo project **pertenece a un `account_id`**.
7. Ningún turno puede consultar el corpus de **otro** project.
8. **No hay** corpus global implícito.
9. **No hay** fallback a "todos los documentos".
10. El **client-sent history** (#260) es contexto conversacional, **no** autoriza acceso a corpus (consistencia con el contrato de continuidad).

---

## 4. Pre-Gate-3 vs Post-Gate-3

### Pre-Gate-3 (demo / staging — estado de HOY)

- El bearer (`OG118_ACCESS_TOKEN`) protege endpoints; es un **speed-bump compartido**, NO auth real.
- Projects funciona para Bernard/demo y para la papelería (cuenta abierta para los niños).
- **Sin claims de multiusuario real.** No se expone como auth.
- Gap aceptado explícitamente: con un solo bearer, cualquiera con el token comparte el mismo espacio. La separación es por `project_id`, no por identidad.

### Post-Gate-3 (Auth0)

- `account_id` = subject del token Auth0.
- `project` pertenece a `account_id`; `corpus` pertenece a `project_id`.
- Uploads requieren `account_id` + ownership del project.
- El runner recibe `project_id` (validado), **no** un `corpus_id` arbitrario del cliente.

---

## 5. APIs mínimas a validar (contrato esperado — sin implementar aquí)

- crear project (server-side genera el id → el id deja de ser client-fabricated);
- listar projects (filtrado por `account_id` post-Gate-3);
- subir archivo a project (ya existe; agregar resolución/validación de ownership);
- bind del project al turno (ya existe vía `active_corpus_binding`; validar que el `project_id` pertenece al caller);
- borrar project;
- borrar/orphanear el corpus asociado al borrar el project;
- exportar/ver metadata de un project.

---

## 6. Riesgos que Bernard debe aceptar

- Sin Gate 3, el bearer de staging **no es auth real** — Projects pre-Gate-3 es demo, no multiusuario.
- Los `project_id` **no deben ser triviales/adivinables** (un UUID v4 server-side está bien; un contador no).
- El `corpus_id` **no debe ser editable por el cliente** (hoy lo es — es el cambio central de PROJ-ACCOUNT-1).
- El endpoint de upload **no debe volverse un dropbox público** (gating por ownership post-Gate-3).
- Borrar un project debe **limpiar el corpus o marcarlo orphaned** (no dejar documentos huérfanos consultables).
- El client-sent history **no autoriza** acceso a corpus.

---

## 7. Decisión propuesta

**Adoptar el modelo `account → projects → corpus` con corpus por proyecto.**

- **Pre-Gate-3:** el bearer protege demo/staging; Projects es de un solo espacio compartido, sin claims de multiusuario.
- **Post-Gate-3 (Auth0):** `account_id` (subject Auth0) gobierna el ownership; `project` pertenece a `account_id`; `corpus` pertenece a `project_id`.
- **El frontend nunca envía `corpus_id` como autoridad** — solo manda `project_id`, y el backend resuelve/valida el corpus.

### Lo que este ADR explícitamente NO hace todavía

No implementar el upload-lifecycle hook · no cambiar endpoints · no tocar auth · no tocar Gate 4 · no tocar voz · no tocar fi-glass.

### Después de este ADR (si Bernard aprueba)

1. **PROJ-ACCOUNT-1** — implementar el boundary de ownership/account: `corpus_id` generado server-side, `project_id` resuelto server-side, modelo `{id, name, createdAt, accountId?}`.
2. upload-lifecycle hook en fi-glass — **solo si sigue haciendo falta** tras PROJ-ACCOUNT-1.
3. Gate 3 / Auth0.
4. Gate 4 (cutover público).

**El siguiente trabajo que mueve la aguja del canary Projects no es UI ni hook — es cerrar este modelo de privacidad.**

---

## La decisión que es de Bernard

Aprobar (o ajustar) el modelo per-project del §7. En particular:

- ¿`corpus_id` server-side desde ya (PROJ-ACCOUNT-1 antes de Gate 3), o se difiere a cuando llegue Auth0?
- ¿El `accountId` se introduce como campo opcional ahora (nullable pre-Gate-3) o solo post-Auth0?

Ambas son reversibles en código; la recomendación es introducir `corpus_id` server-side **antes** de exponer Projects a más gente, porque es el único cambio que cierra el hueco "el cliente elige el corpus".
