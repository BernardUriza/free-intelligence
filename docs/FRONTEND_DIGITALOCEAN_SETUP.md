# 🎨 Frontend en DigitalOcean - Guía Completa

## 🎯 Opciones de Deploy para el Frontend

### Opción 1: **Spaces + CDN** (Recomendado - $5/mes)
✅ Más rápido (CDN global)
✅ Más barato ($5/mes flat)
✅ Auto-scaling sin límites
✅ Deploy con `doctl` o GitHub Actions

### Opción 2: **App Platform** ($5/mes)
✅ Deploy automático desde GitHub
✅ SSL gratis
✅ Logs centralizados
⚠️ Menos rápido que CDN

### Opción 3: **Droplet + Nginx** ($6/mes)
✅ Control total
✅ Puede servir backend + frontend
⚠️ Más mantenimiento

---

## 📦 Opción 1: Spaces + CDN (RECOMENDADO)

### Paso 1: Build de producción

```bash
# En tu proyecto local
cd /Users/bernardurizaorozco/Documents/free-intelligence/apps/aurity

# Build estático de Next.js
pnpm build
pnpm export  # Genera carpeta out/ con HTML estático

# Verificar build
ls -lah out/
```

### Paso 2: Crear Space y subir archivos

```bash
# Instalar doctl si no lo tienes
brew install doctl

# Autenticar
doctl auth init

# Crear Space (bucket S3-compatible)
doctl spaces create fi-aurity-frontend \
  --region nyc3

# Subir archivos
doctl spaces upload \
  fi-aurity-frontend \
  out/* \
  --recursive \
  --acl public-read

# Habilitar CDN (GRATIS)
doctl spaces cdn enable fi-aurity-frontend \
  --region nyc3
```

### Paso 3: Configurar dominio personalizado (opcional)

```bash
# Agregar CNAME record en tu proveedor DNS
# Type: CNAME
# Name: app (o @)
# Value: fi-aurity-frontend.nyc3.cdn.digitaloceanspaces.com
```

### Paso 4: Variables de entorno

Tu frontend necesita apuntar al backend. Edita `.env.production`:

```bash
# apps/aurity/.env.production
NEXT_PUBLIC_API_URL=http://YOUR_DROPLET_IP:7001
# O si usas App Platform:
NEXT_PUBLIC_API_URL=https://your-app.ondigitalocean.app
```

**IMPORTANTE**: Reconstruye después de cambiar variables:
```bash
pnpm build
pnpm export
# Volver a subir a Spaces
```

### URLs Finales

```bash
# URL normal (lenta)
https://fi-aurity-frontend.nyc3.digitaloceanspaces.com

# URL con CDN (RÁPIDA - usa esta)
https://fi-aurity-frontend.nyc3.cdn.digitaloceanspaces.com
```

---

## 🚀 Opción 2: App Platform

### Paso 1: Crear app.yaml

```yaml
# apps/aurity/app.yaml
name: fi-aurity-frontend
region: nyc

static_sites:
- name: frontend
  github:
    repo: BernardUriza/free-intelligence
    branch: main
    deploy_on_push: true
  source_dir: /apps/aurity
  build_command: pnpm install && pnpm build && pnpm export
  output_dir: /out
  catchall_document: index.html
  routes:
  - path: /
  envs:
  - key: NEXT_PUBLIC_API_URL
    value: "https://your-backend.ondigitalocean.app"
    type: SECRET
```

### Paso 2: Deploy

```bash
# Deploy desde CLI
doctl apps create --spec apps/aurity/app.yaml

# O desde UI
# 1. Ir a: https://cloud.digitalocean.com/apps
# 2. Click "Create App"
# 3. Seleccionar GitHub repo
# 4. Branch: main
# 5. Directory: apps/aurity
# 6. Build Command: pnpm install && pnpm build && pnpm export
# 7. Output Directory: out
```

### Paso 3: Configurar variables

```bash
# Obtener app ID
APP_ID=$(doctl apps list --format ID --no-header)

# Actualizar variables
doctl apps update $APP_ID --spec app.yaml
```

---

## 🖥️ Opción 3: Droplet + Nginx

### Paso 1: Crear Droplet

```bash
# Crear droplet con Docker pre-instalado
doctl compute droplet create fi-frontend \
  --region nyc3 \
  --size s-1vcpu-1gb \
  --image ubuntu-22-04-x64 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header) \
  --wait

# Obtener IP
DROPLET_IP=$(doctl compute droplet get fi-frontend --format PublicIPv4 --no-header)
echo "Droplet IP: $DROPLET_IP"
```

### Paso 2: SSH y configurar servidor

```bash
# SSH al droplet
ssh root@$DROPLET_IP

# Instalar Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Instalar pnpm
npm install -g pnpm

# Instalar Nginx
apt-get install -y nginx

# Clonar tu repo
cd /opt
git clone https://github.com/BernardUriza/free-intelligence.git
cd free-intelligence/apps/aurity

# Instalar dependencias
pnpm install

# Build producción
pnpm build

# Configurar Nginx
cat > /etc/nginx/sites-available/aurity << 'EOF'
server {
    listen 80;
    server_name _;

    root /opt/free-intelligence/apps/aurity/out;
    index index.html;

    # Enable gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # API proxy (si backend está en otro servidor)
    location /api/ {
        proxy_pass http://YOUR_BACKEND_IP:7001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Next.js static files
    location /_next/static/ {
        alias /opt/free-intelligence/apps/aurity/out/_next/static/;
        expires 1y;
        access_log off;
    }

    # Try files, fallback to index.html for client-side routing
    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

# Habilitar sitio
ln -s /etc/nginx/sites-available/aurity /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default

# Test y reload
nginx -t
systemctl reload nginx
```

### Paso 3: Configurar auto-deploy (opcional)

```bash
# Crear script de deploy
cat > /opt/deploy.sh << 'EOF'
#!/bin/bash
cd /opt/free-intelligence/apps/aurity
git pull origin main
pnpm install
pnpm build
pnpm export
systemctl reload nginx
EOF

chmod +x /opt/deploy.sh

# Agregar cron job para auto-deploy (cada hora)
crontab -e
# Agregar línea:
# 0 * * * * /opt/deploy.sh >> /var/log/deploy.log 2>&1
```

---

## 🔒 Configuración CORS (Backend)

El backend ya tiene CORS configurado en `backend/app/main.py`, pero verifica:

```python
# backend/app/main.py (línea ~40)
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:9000,http://localhost:9050"
).split(",")
```

**Agregar tu dominio de producción**:

```bash
# En el droplet del backend, edita .env
export ALLOWED_ORIGINS="http://localhost:9000,https://fi-aurity-frontend.nyc3.cdn.digitaloceanspaces.com,http://YOUR_FRONTEND_IP"
```

---

## 📊 Comparación de Opciones

| Feature | Spaces + CDN | App Platform | Droplet + Nginx |
|---------|--------------|--------------|-----------------|
| **Costo** | $5/mes | $5/mes | $6/mes |
| **Velocidad** | ⚡⚡⚡ (CDN global) | ⚡⚡ | ⚡ |
| **Setup** | 5 min | 10 min | 30 min |
| **Mantenimiento** | Cero | Cero | Manual |
| **SSL** | Manual | Automático | Manual (Let's Encrypt) |
| **Auto-scaling** | Ilimitado | Automático | Manual |

---

## 🎯 Recomendación Final

**Para tu app (Aurity):**

```
Frontend: Spaces + CDN ($5/mes)
Backend:  Droplet ($6/mes) o App Platform ($5/mes)
Database: Managed PostgreSQL ($15/mes)
Total:    ~$26/mes
```

**¿Por qué Spaces?**
- ✅ CDN global = usuarios felices en todo México
- ✅ Deploy en 2 comandos
- ✅ Cero mantenimiento
- ✅ Auto-scaling sin límites

---

## 🚀 Quick Start (Spaces + CDN)

```bash
# 1. Build
cd apps/aurity
pnpm build && pnpm export

# 2. Deploy
doctl spaces create fi-aurity --region nyc3
doctl spaces upload fi-aurity out/* --recursive --acl public-read
doctl spaces cdn enable fi-aurity --region nyc3

# 3. Get URL
echo "https://fi-aurity.nyc3.cdn.digitaloceanspaces.com"

# 4. Test
curl https://fi-aurity.nyc3.cdn.digitaloceanspaces.com
```

**¡Listo en 5 minutos!** 🎉

---

## 💡 Pro Tips

1. **Cache Headers**: Spaces CDN cachea automáticamente
2. **Dominio Personalizado**: Usa CNAME para tu dominio
3. **Deploy Script**: Automatiza con GitHub Actions
4. **Environment Variables**: Usa `.env.production` para URLs
5. **Monitoring**: Activa alertas en DO dashboard

---

## 📚 Recursos

- [DigitalOcean Spaces Docs](https://docs.digitalocean.com/products/spaces/)
- [App Platform Docs](https://docs.digitalocean.com/products/app-platform/)
- [doctl CLI Reference](https://docs.digitalocean.com/reference/doctl/)
- [Next.js Static Export](https://nextjs.org/docs/app/building-your-application/deploying/static-exports)

---

**💬 ¿Dudas?** Abre un issue o contacta a Bernard Uriza 🚀
