# OG118-EXTERNAL-TURN-1 — el turno externo se produce y se tira: el proxy corta, el motor termina solo, y Reintentar lo corre dos veces

Status: **Proposed**
Proposed: 2026-10-15 by Claude (dogfood: Bernard reportó "está tardando mucho" en `og118.ai/c/d2742db6…`)

## Qué pasó (recibo, UTC 2026-10-15)

| Hora | Quién | Evento |
|------|-------|--------|
| 19:42:54 | og118-api | arranca en frío (minReplicas 0) |
| 19:43:06 | og118-api | `POST /chat/stream` del mensaje de Göbekli Tepe (elemento Yodo = `external_http_engine`) |
| 19:43:32 | persona-runner | arranca en frío (minReplicas 0, 26 s después del POST) |
| 19:43:40 → 19:43:51 | persona-runner | pipeline warm + prewarm de embeddings (20 s) y abre el topic en AIRE |
| 19:44:41 | og118-api | el proxy corta a los 95 s (`ReadTimeout`); el cliente guarda la conversación con el error |
| 19:45:11 | persona-runner | `turn_pipeline_completed`, 1135 chars + 6 reacciones — **nadie la escuchó** |
| 19:46:06 | persona-runner | extrae 3 facts a la memoria del usuario a partir de ese turno |

La respuesta existe en el motor (se guardó por el pipeline `runner`), og118 ya la había descartado,
y si Bernard pulsa *Reintentar* el motor corre el MISMO texto otra vez: doble gasto, doble escritura
de memoria, y el hilo del motor queda con dos turnos del usuario iguales.

## Lo que se hizo hoy (PR de este mismo día)

El presupuesto de lectura del proxy pasó de 95 s a 150 s: el techo del motor (90 s) **más** el arranque
en frío que corre ANTES de que el reloj del motor empiece. El comentario anterior ("95 > 90, así siempre
corta el motor") comparaba dos relojes que no arrancan juntos. Eso evita ESTE caso; no evita el de un
turno agéntico que legítimamente pase de 150 s, y no recupera la respuesta ya producida.

## Qué falta (lo que esta tarjeta propone)

1. **El corte no debe tirar el turno.** Opciones por costo: (a) el proxy, al cortar, deja al cliente un
   `turn_id` y el motor expone `GET /v1/turn/{id}` para recoger la respuesta tardía; (b) el motor emite
   el turno como stream (SSE) y og118 lo reenvía, como ya hace con el path local — el ping del
   heartbeat deja de ser la única señal de vida.
2. **Reintentar debe ser idempotente** en el motor: mismo `channel_id` + mismo `user_text` dentro de N
   minutos = devolver el turno ya guardado, no correr otro.
3. **Ruta canónica (Art. 6):** el path local ya es un stream de eventos (`runner.py` → `_with_heartbeat`);
   el externo es la excepción single-shot documentada en `external_engine.py`. La forma correcta es
   que el externo converja al mismo contrato de eventos, no un tercer mecanismo.

## La decisión que es de Bernard

- **`persona-runner` con `minReplicas: 1`** quita los 26 s de arranque y el prewarm de 12 s, pero es un
  contenedor de 2 vCPU / 4 Gi encendido 24/7 en ACA (gasto nuevo, del orden de cien dólares al mes
  antes del grant gratuito). Hoy está en 0 con cooldown de 300 s.
- Si no se paga eso, el fix es el punto 1: aceptar que el primer turno tras 5 min de silencio tarda
  más de un minuto y hacer que la UI lo diga y lo espere sin perder la respuesta.

## Status / next step

Proposed. Siguiente paso: Bernard elige entre pagar la réplica caliente o el punto 1 (a/b); el 2 va en
cualquier caso. Evidencia: logs de `persona-runner` y `og118-api` del 2026-10-15 19:42–19:46 UTC
(`az containerapp logs show`).
