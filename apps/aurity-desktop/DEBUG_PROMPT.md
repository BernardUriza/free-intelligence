# Debug Prompt: Aurity Desktop (Tauri + Next.js) No Carga Correctamente

## Contexto
Estoy desarrollando **Aurity Desktop**, una aplicación nativa usando Tauri 2.0 que envuelve un frontend Next.js 16 y un backend FastAPI como sidecar. La ventana de Tauri se abre pero el contenido no carga correctamente.

## Arquitectura
```
apps/aurity-desktop/
├── src-tauri/
│   ├── src/main.rs          # Spawn backend sidecar, health check, inject URL
│   ├── tauri.conf.json      # devUrl: http://localhost:9050
│   └── binaries/aurity-backend-aarch64-apple-darwin  # Shell script → Python
└── (usa apps/aurity/ como frontend)

Puertos:
- Backend sidecar: 7051 (desktop dev), 7052+ (prod dinámico)
- Frontend dev: 9050
- Cloud usa: 7001 (backend), 9000 (frontend)
```

## El Problema
1. `cargo tauri dev` inicia correctamente
2. Backend sidecar arranca en puerto 7051, health check pasa ✅
3. Frontend Next.js intenta compilar `/chat`
4. **CRASH**: Node.js muere con "JavaScript heap out of memory"
5. La ventana Tauri queda en blanco o con error de carga

## Lo Que He Intentado
1. `NODE_OPTIONS="--max-old-space-size=8192"` pasado a cargo tauri dev - No se propaga
2. Modificar `package.json` script `dev:desktop` para incluir NODE_OPTIONS - Mismo resultado
3. El frontend funciona perfecto en browser (`pnpm dev:desktop` directo)
4. Playwright E2E tests pasan (4/4) cuando corro backend y frontend manualmente

## Logs Relevantes
```
[Aurity] Backend is healthy on port 7051
○ Compiling /chat ...
✓ Compiled in 85.5s

FATAL ERROR: Ineffective mark-compacts near heap limit Allocation failed - JavaScript heap out of memory
```

## Archivos Clave
- `apps/aurity-desktop/src-tauri/tauri.conf.json`: beforeDevCommand ejecuta `pnpm --filter aurity dev:desktop`
- `apps/aurity/package.json`: script `dev:desktop` con NODE_OPTIONS
- `apps/aurity-desktop/src-tauri/src/main.rs`: Lógica de sidecar y port injection

## Preguntas Específicas
1. ¿Cómo propagar NODE_OPTIONS correctamente desde Tauri al proceso Node.js hijo?
2. ¿Hay una forma de pre-compilar el frontend antes de `cargo tauri dev` para evitar el OOM?
3. ¿Debería usar `next build` + servir estático en lugar de `next dev` para Tauri?
4. ¿El problema es Turbopack (Next.js 16 default) consumiendo demasiada memoria?

## Entorno
- macOS Darwin 25.1.0 (Apple Silicon M1/M2)
- Node.js 24.10.0
- Next.js 16.0.10 (Turbopack)
- Tauri 2.0
- Rust stable

## Objetivo
Hacer que la ventana Tauri cargue el frontend Next.js correctamente, ya sea en modo dev o usando un build pre-compilado.
