# GATE4 — Human Smoke Runbook

**Estado del roadmap:** `RC-BLOCKED-BY-HUMAN/DEPLOY-VERIFICATION` — 45/47 checks DONE, 0 P0/P1 autónomos abiertos.
**Generado:** 2026-06-30 vía `/exchange-coagent` (coagent: AURITY Prompt Engineer - og118).

Los 2 checks restantes NO se cierran por código ni por memoria — requieren manos/oídos/sesión reales.
Marcarlos DONE sin correr el smoke vivo sería fake-green (Constitution Art. 2). Este runbook deja los
pasos exactos para que Bernard los cierre con mínima fricción.

Referencias: `GATE4-CUTOVER-READINESS.md` filas #12 (Voice TTS ⬜) y #13 (Voice STT ⬜);
`ROADMAP-TO-REPLACE-CHATGPT.html` pendientes `AUDIO-HUMAN-SMOKE` + `VOICE-GATEWAY-AUTH-SMOKE`.

---

## Bloque A — AUDIO-HUMAN-SMOKE (FIGLASS audio durable, pausa/reanuda)

**Quién:** Bernard (mic + oídos). **Dónde:** `https://staging.og118.ai/` autenticado (login Google/Auth0).

1. Abrir `staging.og118.ai` y loguearse (Google → Auth0).
2. Iniciar grabación. Decir **frase A** (ej. "uno dos tres canary alfa").
3. **Pausar.** Debe montarse el player con el audio YA grabado.
4. **Reproducir el preview** → la frase A debe oírse audible (no solo dot+tiempo).
5. **Reanudar.** Decir **frase B** (ej. "cuatro cinco seis canary beta").
6. **Pausar** de nuevo → el preview ahora debe contener **A + B** spliceados.
7. **Stop** → entrega el WAV completo.
8. **Transcribir** → el texto debe contener frase A y frase B en orden.
9. El texto transcrito aparece en el composer / flujo esperado.
10. **Enviar** ese texto al chat → respuesta normal.
11. **Consola limpia** (sin errores rojos).

**PASS si:** preview audible real en cada pausa, splice A+B correcto, transcripción ordenada, consola limpia.
Al pasar → marcar `AUDIO-HUMAN-SMOKE` DONE en el roadmap.

---

## Bloque B — VOICE-GATEWAY-AUTH-SMOKE (TTS/STT vía gateway susurro)

**Quién:** Bernard / ops. **Pre-requisito deploy:** vars/secrets GitHub + ACA apuntando a
`sus.bernarduriza.com` (`OG118_TTS_ENDPOINT/_DEPLOYMENT`, `OG118_STT_ENDPOINT/_DEPLOYMENT`).
Sin esto, el smoke fallará con 404/502 upstream (causa raíz histórica de qa-tts-502 / qa-stt-502).

**Dónde:** `https://staging.og118.ai/` autenticado, con DevTools → Network abierto.

### TTS
1. En una respuesta del asistente, click **Escuchar**.
2. Network: `/tts/synthesize` → **200** (NO 401/404/502/503).
3. El audio se reproduce audible.

### STT
4. Grabar una **frase canary** con el mic real.
5. Network: `/stt/transcribe` → **200**.
6. El texto transcrito es razonable y entra al composer.

**PASS si:** ambos endpoints 200, audio audible, transcripción razonable, sin 401/404/502/503, consola limpia.
Al pasar → marcar filas #12 (Voice TTS) y #13 (Voice STT) ✅ en `GATE4-CUTOVER-READINESS.md` y
`VOICE-GATEWAY-AUTH-SMOKE` DONE en el roadmap.

---

## Después de ambos PASS

- Roadmap → **47/47**, Gate 4 = *technical readiness complete*.
- La decisión de **cutover apex/DNS (og118.ai público)** pasa a Bernard — es su llamada irreversible,
  no se ejecuta desde el relay.
