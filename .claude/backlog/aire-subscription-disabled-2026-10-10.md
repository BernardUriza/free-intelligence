# AIRE-SUB-DISABLED-1 — la org de vegdevida apagó el OAuth y el rotor no lo reconocía como falla

Status: In progress — remedio 1 VIVO y verificado (PR #542, `257569e1`, deploy 18:0x CST; turno real del iPhone 18:09 contestó `PONG`). Falta la decisión de Bernard sobre el respaldo: hoy la cadena vive sobre UNA cuenta OAuth
Proposed: 2026-10-10 by Claude (diagnóstico sólo-lectura pedido por Bernard)

## Qué se observó

2026-10-10 17:54 CST: un turno del iPhone de og118 → `og118-api` → AIRE devolvió HTTP 200 con el
SSE `{"type":"text","text":"Your organization has disabled Claude subscription access for Claude
Code · Use an Anthropic API key instead, or ask your admin to enable access"}` — pintado como si
fuera la respuesta de og118.

## Evidencia (2026-10-10 ~17:56–18:05 CST, sólo lectura)

El detalle con prefijos, hashes y host vive fuera del repo (este repo es público):
`~/.secrets/oauth-map.md` y la copia local del reporte del diagnóstico.

Prueba directa contra `api.anthropic.com/v1/messages` (`claude-haiku-4-5`, `max_tokens: 5`):

| slot del rotor | cuenta | HTTP | error |
|---|---|---|---|
| oauth-primary | vegdevida | **403** | `permission_error` · `oauth_not_allowed_for_organization` |
| oauth-backup | bernardurizadev | **200** | contestó; 5h y 7d `allowed`, utilización 7d 0.08 |
| api-key-fallback | org metered | **400** | `credit balance is too low` |
| lend | org metered | **400** | mismo |
| lane BAIR | — | — | sin key armada |

El 403 es lo que el CLI pinta como "Your organization has disabled Claude subscription access for
Claude Code": bloqueo a nivel ORG, no token revocado (401) ni cuota (429).

**Por qué llegó al usuario:** `LIMIT_PHRASE` (`apps/aire-server/server/aire/engine/credentials.py`)
no conocía ese texto ni `permission_error`; el turno contó como éxito, el primario nunca se enfrió y
el backup vivo nunca entró. Última línea `CREDENTIAL-EXHAUSTED` del journal: 2026-10-08 18:59 UTC.

**Alcance:** toda la cadena compartida. Apariciones en `claude_session_store` (conteo, sin leer
contenido): `canary` ×2 (07:26), `bair-gatekeep` ×5 (13:35–14:31), og118 iPhone ×1 (17:54). Discord no
tuvo tráfico en la ventana, pero usa la misma cadena.

**Desde cuándo:** primera aparición registrada 2026-10-10 07:26 CST (13:26 UTC), turno del canary.
La causa del bloqueo en la org de vegdevida NO está verificada; sólo el rótulo del sistema.

## Remedios

1. **El rotor reconoce el error** — `disabled claude subscription access|permission_error` en
   `LIMIT_PHRASE`, con prueba del texto vivo. $0, cubre a todos los consumidores, mismo patrón que
   `e52386d7`. **Hecho en PR** (este archivo viaja en él). El primario se re-prueba cada hora
   (cooldown 1h) y cae al backup en el mismo turno.
2. Promover el backup a primario sin código (re-componer `/etc/aire/env` con
   `apps/aire-server/server/infra/provision-do.sh`). Deja la cadena sin backup OAuth.
3. Re-habilitar el OAuth en la org de vegdevida — login de Bernard, sin runbook.
4. Mintear token en otra cuenta Max y propagar con
   `~/Documents/engineering-playbook/scripts/rotate-claude-oauth.sh` (el droplet es paso manual).
5. Metered (recargar créditos / key del lane BAIR): **gasto**, sólo si Bernard lo decide
   (`contencion-oauth-no-se-arregla-con-dinero.md`).

## La decisión que es de Bernard

- Con el remedio 1 la cadena vive sobre UNA cuenta OAuth (bernardurizadev). Si vegdevida se
  re-habilita (3) o se mintea otra (4) para recuperar el respaldo.

## Deuda de diseño que este incidente vuelve a mostrar

Quinta vez en un mes (09-03, 09-08, 09-28, 10-08, 10-10) que un error del proveedor llega como TEXTO
de un turno "exitoso" y se pinta como respuesta, hasta que alguien agrega su frase. El servidor
debería emitir un frame de error, no `text`, y el rotor clasificar por el sobre del error del
CLI/SDK, no por frases.
