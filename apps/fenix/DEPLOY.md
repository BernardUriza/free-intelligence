# Despliegue de Fénix

Estado al 30-jul-2026. Lo que ya existe, lo que falta, y por qué cada cosa.

## El dominio — LISTO

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

## Lo que falta, en orden

### 1. Llave de API de Anthropic — bloqueante, y es de Bernard

`console.anthropic.com` → crear llave + cargar saldo. **No existe ninguna hoy**
(`~/.secrets` sólo tiene tokens OAuth `oat01`, que son de suscripción).

Servir a la papelería y al cibercafé con el token de suscripción rompe el ToS de
Anthropic. `arranque.py` lo vuelve invariante: el servidor **se niega a
arrancar** sin `ANTHROPIC_API_KEY`, y también si detecta las dos credenciales a
la vez — porque el SDK elige el modo leyendo el entorno y ahí no se puede
afirmar cuál paga.

**Cuánto cargar:** $50 USD alcanza de sobra para lanzar sólo el tutor. Medido
sobre turnos reales:

| Superficie | por turno | mes realista |
|---|---|---|
| Tutor (los niños) | ~$0.011 | ~$50 · techo con la cuota: $158 |
| Mostrador (cotizar) hoy | ~$0.30–0.60 | $150–270 |

El mostrador NO se lanza todavía: cuesta 30× más por turno **y** da peor
resultado que claude.ai (ver `EXPERIMENTO.md` §benchmark). Su arreglo —poner la
lista maestra en contexto en vez de recuperarla en 17 llamadas RAG— baja el
costo y sube la calidad a la vez.

### 2. Variables del despliegue

Estas cuatro deciden si el despliegue es seguro. Sin las dos primeras el
servidor no arranca, a propósito.

```
ANTHROPIC_API_KEY=…          # sin ella no arranca (ToS)
FENIX_ADMIN_TOKEN=…          # sin él los expedientes quedan abiertos; no arranca
OG118_ACCESS_TOKEN=…         # sin él las rutas quedan abiertas a internet
FENIX_PROXY_CONFIABLE=1      # detrás del ingress de ACA, o todos comparten un cubo de cuota
FENIX_ADMIN_EMAILS=lidia@…,ximena@…
FENIX_CUOTA_POR_MINUTO=8     # defaults; suben o bajan sin redeploy
FENIX_CUOTA_POR_HORA=60
```

**NUNCA** poner `CLAUDE_CODE_OAUTH_TOKEN` en el despliegue.

### 3. Infra — clonar el patrón de og118, no inventarlo

`apps/og118/DEPLOY.md` + `.github/workflows/og118-backend.yml` son la ruta
canónica: ACR → Azure Container Apps con Azure Files montado en `/opt/fi/data`,
`--min-replicas 1 --max-replicas 1`. Ese "1 réplica" no es un detalle: la cuota
de turnos y las sesiones viven en memoria del proceso, así que con varias
réplicas dejan de ser globales.

El web va en Azure Static Web Apps, igual que og118.

### 4. DNS

`serviciosfenix.com.mx` está en Namecheap con su DNS por defecto. Al desplegar:
CNAME del web al hostname de la SWA, y el backend en un subdominio propio.
