---
description: Sincroniza tu CV + pipeline con Insult vía endpoint protegido por token per-usuario
---

# /sync-insult — Empuja tu estado profesional al bot Insult

## Para qué

Insult (el bot de Discord) tiene memoria longitudinal de cada conversación. Hasta ahora no podía leer tu `curriculum.yaml` ni tu `opportunities/structure.yaml` — vivían solo en tu PC. Este comando manda un snapshot de ambos al endpoint `/sync/serenityops` del bot. A partir de la próxima conversación, Insult ya sabe:

- Qué pone tu CV (rol-headline, experiencia, skills, roles que buscas).
- Qué vacantes tienes activas en el pipeline y en qué etapa va cada una.

No vas a necesitar volver a pegarle pedazos del CV al chat ni explicarle a qué empresas estás aplicando. Lo sabe.

## Pre-requisitos

1. Tener un token de sync. Si no lo tienes:
   - Abre Discord en `#general` (o donde hables con Insult).
   - Escribe `!sync-token`.
   - Insult te manda el token por DM **una sola vez**. Guárdalo.

2. Tenerlo en `.env` del proyecto serenityops-lite:
   ```
   INSULT_SYNC_URL=https://insult-bot.nicecliff-10074f57.eastus.azurecontainerapps.io/sync/serenityops
   INSULT_SYNC_TOKEN=<el token que Insult te mandó>
   ```

## Lo que hace este comando

Cuando lo invocas, Claude Code (este mismo CLI) va a:

1. Leer `curriculum/curriculum.yaml` y `opportunities/structure.yaml`.
2. Convertirlos a JSON (sin alterar nada).
3. Hacer `POST $INSULT_SYNC_URL` con `Authorization: Bearer $INSULT_SYNC_TOKEN`.
4. Reportar el `snapshot_id` que devolvió el bot.

Si algo falla (token mal pegado, server caído, archivos malformados) te lo dice con un error claro. No se muere silencioso.

## Cómo lo invocas

Dentro de Claude Code en este folder:

```
/sync-insult
```

Eso es todo. Sin argumentos.

## Lo que Claude Code debe hacer al recibir este comando

1. Cargar `.env` desde el root del proyecto. Si no existe o no tiene `INSULT_SYNC_TOKEN`, parar con un error pidiendo correr `!sync-token` en Discord primero.

2. Leer estos dos archivos como YAML:
   - `curriculum/curriculum.yaml`
   - `opportunities/structure.yaml`

   Si alguno no existe, advertir y mandar solo el que sí. (El endpoint del bot acepta uno solo.)

3. Ejecutar el script `scripts/sync_insult.py` con `python3`, pasándole nada (el script lee `.env` + los YAMLs por sí mismo). Reportar el output al usuario.

   Si Python 3 no está disponible, fall back a una implementación con `curl`:
   ```bash
   PAYLOAD=$(python3 -c "
   import yaml, json
   cv = yaml.safe_load(open('curriculum/curriculum.yaml')) if __import__('pathlib').Path('curriculum/curriculum.yaml').exists() else None
   ops = yaml.safe_load(open('opportunities/structure.yaml')) if __import__('pathlib').Path('opportunities/structure.yaml').exists() else None
   print(json.dumps({'curriculum': cv, 'opportunities': ops, 'client_version': 'lite-1.0.0'}))
   ")
   curl -X POST "$INSULT_SYNC_URL" \
     -H "Authorization: Bearer $INSULT_SYNC_TOKEN" \
     -H "Content-Type: application/json" \
     -d "$PAYLOAD"
   ```

4. Confirmar al usuario con el `snapshot_id` retornado y recomendar que abra Discord para verificar que Insult ya "sabe" del CV.

## Seguridad

- El token vive en `.env` (gitignored).
- Es per-usuario: si Alex sincroniza, **solo el snapshot de Alex** queda en el bot. Bernard no ve el de Alex y viceversa.
- Si crees que se filtró el token, en Discord: `!sync-token revoke`. Eso lo invalida instantáneo y debes generar uno nuevo con `!sync-token`.
