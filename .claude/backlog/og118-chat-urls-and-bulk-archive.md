# OG118-CHAT-URLS-1 — cada chat con su URL, `/` como chat nuevo, y archivar en lote

Status: **Done 2026-10-09** (residual: el `returnTo` del login de Auth0 no se ha probado con un login real)
Proposed: 2026-10-09 by Bernard ("quiero poder rápidamente archivar todos mis chats… un modal"; "que cada chat me otorgue un identificador único de URL, como ChatGPT")

## What it is

Dos pedidos del mismo día y el bug que los juntó: con los 45 chats archivados, `/` le seguía mostrando uno ("Probe F5…"), porque `useConversationLibrary` abría `list[0]` sin mirar `archivedAt`.

## Lo que se entregó (main, verificado en app.og118.ai)

| PR | Qué | Recibo |
|---|---|---|
| #533 `7817bf0`, #534 `a0893e3` | `archiveConversations(ids)` (concurrencia 4, un solo refresh, nunca lanza: devuelve los fallidos) + `ConversationArchiveDialog` sobre `<dialog>` nativo; todo lo no fijado empieza marcado, los fijados arriba | Prod: 32 chats, 30 marcados, los 2 "razzia" fijados arriba sin marcar, "Archivar 30 chats"; abierto y cancelado. Bernard luego archivó todo |
| #535 `bd8466c` | El default ya no abre un archivado; `initialActiveId` (la URL decide); `useConversationUrl` (`/c/<id>` guardado, `/` nuevo); `staticwebapp.config.json` rewrite `/c/*`; `returnTo` en el login | SWA responde 200 en `/c/<id>`; `/` con todo archivado → 0 mensajes |
| #536 `630ab01` | Abrir un chat desde `/` hacía `replaceState` (Atrás sacaba de la app): ahora `push`, y `replace` sólo cuando el mismo chat recibe su primer guardado | Prod: abrir chat → historial 3→4; Atrás → `/` y Adelante → `/c/<id>`, misma página (marcador en `window` intacto); carga directa de `/c/<id>` abre ese chat; chat nuevo en `/` + mensaje → `/c/348d2969-…` con historial sin crecer. El chat de prueba quedó archivado |

## Residual

- **`returnTo` de Auth0**: entrar a `/c/<id>` sin sesión debería volver a ese chat tras el login. Probarlo requiere cerrar sesión y volver a entrar (el átomo es la contraseña de Bernard).
- Abrir un chat archivado por URL no lo marca en el sidebar mientras la sección de archivados esté colapsada.
