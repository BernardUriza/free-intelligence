# Despliegue de Fénix

Estado al 6-ago-2026, verificado contra lo que está corriendo — no contra lo que
debería estar. Lo anterior era un plan escrito el 30-jul; el tutor ya está en
línea y atendiendo, así que este documento pasa a describir lo vivo.

## En línea hoy

| | |
|---|---|
| Portada | **https://www.serviciosfenix.com.mx** — 200, con la promesa y el botón de WhatsApp |
| Tutor (los niños) | **https://www.serviciosfenix.com.mx/app/** — responde; verificado preguntando "¿cuánto es 7 por 8?" |
| Modelo del tutor | `claude-sonnet-4-5` |
| Web | Azure Static Web Apps `fenix-web` (grupo `og118-rg`) |
| Backend | Azure Container Apps `fenix-api` (grupo `og118-rg`), 1 réplica |
| Credencial | `ANTHROPIC_API_KEY` propia (secreto `FENIX_ANTHROPIC_API_KEY`), NO la suscripción |
| Cuota pública | 8 turnos/minuto, 60/hora por IP — **cortando de verdad**, comprobado en producción |

El **mostrador NO se lanza todavía**: cuesta ~30× más por turno que el tutor y da
peor resultado que claude.ai (ver `EXPERIMENTO.md` §benchmark). Su arreglo —poner
la lista maestra en contexto en vez de recuperarla en 17 llamadas RAG— baja el
costo y sube la calidad a la vez. Mientras tanto el equipo cotiza en claude.ai.

## El dominio

| | |
|---|---|
| Dominio | **`serviciosfenix.com.mx`** |
| Registrador | Namecheap (cuenta `bernarduriza`) |
| Orden | `209765627` · 30-jul-2026 |
| Costo | $10.48 USD el 1er año · renueva a $13.98 |
| Expira | 30-jul-2027, con auto-renovación ON |
| Privacidad | WHOIS oculto, gratis de por vida |

`serviciosfenix.com` estaba tomado desde 2013 (Tucows, renovado hasta 2027) y
`papeleriafenix.com` también. El `.com.mx` calza con la razón social y lo lee
igual una mamá en WhatsApp que un niño tecleándolo.

**Nota para la próxima compra:** el cobro rebotó dos veces con
`Insufficient funds`. Ese código lo devuelve el banco emisor y los bancos
mexicanos lo usan también cuando bloquean un cargo internacional en USD — no
siempre es saldo. Namecheap sólo repite lo que el emisor contesta.

## Variables del despliegue

Las dos primeras deciden si el despliegue es seguro; sin ellas el servidor **se
niega a arrancar**, a propósito (`arranque.py`).

```
ANTHROPIC_API_KEY=…          # sin ella no arranca (ToS: los niños son terceros)
FENIX_ADMIN_TOKEN=…          # sin él los expedientes quedan abiertos; no arranca
FENIX_TUTOR_PASSWORD=…       # sin ella la URL ES la credencial; no arranca
FENIX_PROXY_CONFIABLE=1      # detrás del ingress de ACA, o todos comparten un cubo de cuota
FENIX_ADMIN_EMAILS=lidia@…,ximena@…
FENIX_CUOTA_POR_MINUTO=15    # defaults; suben o bajan sin redeploy
FENIX_CUOTA_POR_HORA=60
FENIX_BITACORA_PATH=…        # opcional; por defecto, junto a los expedientes
HDF5_USE_FILE_LOCKING=FALSE  # HDF5 pelea con SMB; seguro porque hay una sola réplica
```

### Las tres credenciales protegen cosas distintas

| | Separa | Se pega en | Si se filtra |
|---|---|---|---|
| `FENIX_ADMIN_TOKEN` | las PC de adentro de las de afuera | las PC del mostrador | alguien ve los expedientes de las familias |
| `FENIX_TUTOR_PASSWORD` | **la papelería de internet** | las PC del ciber (y el celular de quien quiera usarlo) | vuelve el riesgo de hoy: gasto ajeno, acotado por la cuota |
| La cuota de turnos | nada — **acota el gasto** | no se pega, es del servidor | — |

La contraseña del tutor **no impide que un niño se la pase a otro**: en una sala
donde cualquiera se sienta, un secreto compartido acaba escrito en un papel. Ése
no es su trabajo. Su trabajo es que quien descubra la URL desde fuera —un
escáner, un enlace reenviado, un buscador— no pueda gastar la llave de API. El
techo de gasto sigue siendo la cuota, y por eso van juntas.

### Los dos límites de la cuota no se mueven juntos

Las dos PC del ciber salen por el mismo router: para la cuota son **un solo
cliente** y comparten el cubo.

- **Por minuto (15)** es lo que se siente en la sala. Subirlo NO sube el techo de
  gasto, sólo permite que dos niños pregunten a la vez sin estorbarse.
- **Por hora (60)** ES el techo: lo máximo que alguien puede quemar en una hora.
  Se sube con cuidado aunque haya contraseña.

Ambos se cambian sin redeploy (`az containerapp update --set-env-vars`).

### La bitácora — qué se preguntó y desde dónde

Una línea JSON por turno en el volumen (`bitacora.jsonl`, rota a los 5 MB
conservando una generación): cuándo, IP real del visitante, rol, la pregunta
recortada a 300 caracteres, y si se cortó por cuota o por falta de contraseña.
No guarda la respuesta del modelo ni ningún nombre.

Se lee desde el mostrador, nunca desde la sala:

```
GET /expedientes/bitacora?limite=200     (requiere X-Fenix-Admin)
```

El **resumen va primero a propósito**: lo que se mira al abrirla no es la lista
de preguntas, es si hay una IP desconocida acumulando turnos.

Escribir la bitácora nunca tumba un turno: si el disco falla, el niño igual
recibe su respuesta y la línea se pierde.

**NUNCA** poner `CLAUDE_CODE_OAUTH_TOKEN`: es credencial de suscripción y su
licencia es de uso personal.

### NUNCA poner `OG118_ACCESS_TOKEN` — y por qué esta línea existe

Hasta el 6-ago este documento pedía esa variable *"sin él las rutas quedan
abiertas a internet"*. Era falso aquí, y dejó **al cibercafé mudo durante días**.

Ese bearer es de og118, que es una app de una sola cuenta. Fénix atiende a dos
públicos y separa distinto: el mostrador se identifica con `FENIX_ADMIN_TOKEN` y
lo público lo acota la cuota de turnos. Un bearer no protege una PC donde
cualquiera se sienta, porque para usarlo habría que dejárselo escrito al lado.

Con la variable puesta, el bearer de og118 corre **antes** que la puerta de Fénix:
`/chat/stream` contestaba `401` y la cuota nunca llegaba a autorizar a nadie.
Y como `/expedientes/rol` es ruta propia y sí pasaba, la página cargaba entera
—logo, tarjetas, "Pregunta lo de tu tarea"— y el niño recibía un error al
preguntar. Nada fallaba en los logs.

`arranque.prohibir_candado_heredado()` ahora se niega a arrancar si la variable
reaparece. El workflow tampoco la inyecta y la remueve del Container App en el
mismo comando que sube la imagen.

## Quién puede tocar qué

| Ruta | Sin token de mostrador | Con `X-Fenix-Admin` |
|---|---|---|
| `/chat/stream` | permitido, con cuota | permitido, sin cuota (no se corta una venta) |
| `/expedientes/rol` | 200 (`admin:false`) | 200 (`admin:true`) |
| `/conversations`, `/projects` | **404** | 200 |
| `/tts/synthesize`, `/stt/transcribe` | **404** | 200 |

Los expedientes responden **404 y no 403**: para una PC del cibercafé esa
superficie no existe; un 403 confirmaría que hay algo detrás que vale la pena
adivinar. El audio está cerrado porque ningún cliente de Fénix lo llama y
transcribir cuesta por segundo — si algún día el mostrador quiere dictado, ya
entra con su token.

## Infra — clonar el patrón de og118, no inventarlo

`apps/og118/DEPLOY.md` + `.github/workflows/og118-backend.yml` son la ruta
canónica: ACR → Azure Container Apps con Azure Files montado en `/opt/fi/data`,
`--min-replicas 1 --max-replicas 1`. Ese "1 réplica" no es un detalle: la cuota
de turnos y las sesiones viven en memoria del proceso, así que con varias
réplicas dejan de ser globales y el techo de gasto deja de ser un techo.

El despliegue lo hace `.github/workflows/fenix-backend.yml` en cada push a `main`
que toque `apps/fenix/server/**`, `apps/packages/fi-core/**` o
`apps/packages/fi-runner/**`.

## DNS

`serviciosfenix.com.mx` vive en Namecheap con su DNS por defecto
(`dns1/dns2.registrar-servers.com`).

- **`www`** → CNAME al hostname de la SWA. Estado `Ready`, TLS válido hasta
  enero 2027. **Es la URL que se comparte.**
- **El ápice (sin `www`)** → **ALIAS**, no CNAME: un CNAME en la raíz es inválido
  por RFC, choca con los registros SOA/NS obligatorios. Ya resuelve a la misma IP
  que `www`.

**El ápice todavía no tiene certificado.** Azure valida la raíz por token TXT, no
por CNAME — `az staticwebapp hostname set … --validation-method dns-txt-token`.
Sin ese flag el comando pide un CNAME y falla con `CNAME Record is invalid`, que
es la pista falsa que costó tiempo. Falta publicar en Namecheap:

```
Tipo: TXT   ·   Host: @   ·   Valor: el validationToken que devuelve
az staticwebapp hostname show -n fenix-web -g og118-rg \
  --hostname serviciosfenix.com.mx --query validationToken -o tsv
```

Mientras no esté, `https://serviciosfenix.com.mx` no responde y `www` sí. No es
grave: `www` es la que se comparte y la que trae la tarjeta de WhatsApp.

## Verificar un despliegue — qué mirar y qué no

Un `200` en `/app/` **no prueba nada**: la página carga aunque el backend
rechace cada pregunta. La comprobación que no puede mentir es preguntar algo
real en https://www.serviciosfenix.com.mx/app/ y ver la respuesta.

```bash
# la cuota, sin gastar un turno de modelo: un cuerpo inválido consume cuota
# (la puerta corre antes de la validación) y devuelve 422 hasta que corta
API=https://fenix-api.thankfulmoss-53b8b5c9.eastus2.azurecontainerapps.io
for i in $(seq 1 10); do
  curl -sS -o /dev/null -w "%{http_code} " -X POST "$API/chat/stream" \
    -H 'content-type: application/json' -d '{}'
done   # esperado: 422 ×8 y luego 429 con CUOTA_AGOTADA
```

Los tests del servidor corren con el intérprete de og118, no con el `.venv` raíz
(que no tiene `fi_runner`):

```bash
cd apps/fenix/server
FENIX_ADMIN_TOKEN=token-de-prueba ANTHROPIC_API_KEY=sk-ant-api03-falsa \
  ../../og118/server/.venv/bin/python -m pytest tests/ -q
```

**Ojo con lo que los tests NO ven:** en local `OG118_ACCESS_TOKEN` no existe, así
que el bearer heredado deja pasar todo y la cuota se ejercita como si nada —
verde en local, mudo en producción. Por eso
`test_el_candado_de_og118_deja_mudo_al_cibercafe` pone la variable a propósito.
Un test que no reproduce la configuración del contenedor no habla del contenedor.

## Costo medido

| Superficie | por turno | mes realista |
|---|---|---|
| Tutor (los niños) | ~$0.011 | ~$50 · techo con la cuota: $158 |
| Mostrador (cotizar) hoy | ~$0.30–0.60 | $150–270 |
