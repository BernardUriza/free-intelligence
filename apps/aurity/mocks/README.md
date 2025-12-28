# Aurity Frontend Mocks (MSW)

Enable UI flows without a running backend.

## How to enable
- Env flag: set `NEXT_PUBLIC_USE_MOCKS=true` (or legacy `NEXT_PUBLIC_MOCK_BACKEND=true`).
- Runtime toggle: `localStorage.setItem('USE_MOCKS', 'true')` then refresh.

`MockBootstrap` in `app/layout.tsx` starts the MSW worker only in the browser when flags are active.

## What is mocked
- Medical workflow: stream, checkpoints, SOAP, diarization, orders, monitor, timeline, KPIs, clinic media, system disk/clear-memory, sessions list.
- Assistant: chat, SSE stream, history search, WebSocket sync.
- Check-in: QR/session/identify/actions/complete + waiting-room WS.
- Clinics/doctors/appointments/membership CRUD.
- Admin: personas, catalog models/sources, system resources/running/compatibility.
- Exports, audit logs, policy.

## Extending
- Add fixtures under `mocks/fixtures/*`.
- Add handlers under `mocks/handlers/*` and export via `handlers/index.ts`.
- For streaming, use `mocks/utils/sse.ts`. For WS, use `ws.link(...)` handlers.
