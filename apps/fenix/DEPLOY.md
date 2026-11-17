# Fénix — la página de la papelería

Desde el 17-nov-2026 Fénix es sólo esto: la página pública de Servicios Papeleros
Fénix en https://www.serviciosfenix.com.mx. El asistente (el mostrador, el tutor
del cibercafé, su servidor y sus datos) se dio de baja ese día; su código vive en
el historial de git anterior a esa fecha.

## Qué hay

| Pieza | Dónde |
|---|---|
| Página | `apps/fenix/web` — Next.js con `output: 'export'`, una sola ruta (`/`) |
| Hosting | Azure Static Web App `fenix-web` (grupo `og118-rg`, plan Free) |
| Dominio | `www.serviciosfenix.com.mx`, CNAME al hostname de la SWA |
| Marca | `apps/fenix/branding` y `apps/fenix/web/public/branding` |

No hay backend, ni base de datos, ni variables de entorno.

## Publicar un cambio

No tiene workflow: se publica a mano.

```bash
pnpm --filter fenix-web build
cd apps/fenix/web
T=$(grep '^AZURE_SWA_TOKEN_FENIX=' ~/.secrets/fenix-swa-token.txt | cut -d= -f2-)
npx -y @azure/static-web-apps-cli deploy ./out --deployment-token "$T" --env production
```

Verifica en el dominio real, no en el hostname de Azure:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://www.serviciosfenix.com.mx/
```

## El dominio

`www` es un CNAME a la SWA, validado por `dns-txt-token`. El estado del enlace:

```bash
az staticwebapp hostname show -n fenix-web -g og118-rg \
  --hostname www.serviciosfenix.com.mx --query status -o tsv
```

El apex (`serviciosfenix.com.mx` sin `www`) no sirve la página.
