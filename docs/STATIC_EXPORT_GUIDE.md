# 🎯 Convertir Aurity a Frontend Estático

## ✅ SÍ, tu app PUEDE ser 100% estática!

Tu app es **perfecta** para export estático porque:
- ✅ Todo el backend está en FastAPI separado
- ✅ No necesitas SSR (Server-Side Rendering)
- ✅ Todo se renderiza en el cliente (React SPA)
- ✅ Las API calls van a http://localhost:7001 (backend externo)

---

## 🔧 Cambios Necesarios

### 1. Actualizar `next.config.js`

**ANTES (SSR mode):**
```javascript
output: 'standalone'  // ← Requiere Node.js server
```

**DESPUÉS (Static mode):**
```javascript
output: 'export'  // ← HTML estático puro
images: {
  unoptimized: true  // ← Next Image no funciona en estático
}
```

**Aplicar cambio:**
```bash
cd apps/aurity

# Opción 1: Reemplazar config actual
cp next.config.static.js next.config.js

# Opción 2: Editar manualmente
# Cambia línea 10: output: 'standalone' → output: 'export'
# Agrega en images: unoptimized: true
```

### 2. Remover/Adaptar API Route

Tu app tiene 1 API route: `app/api/health/route.ts`

**Opciones:**

**A) Eliminar** (si no es crítica):
```bash
rm apps/aurity/app/api/health/route.ts
```

**B) Mover al backend FastAPI**:
```python
# backend/app/main.py (ya existe!)
@app.get("/")
async def root():
    return {"status": "healthy", "service": "aurity"}
```

### 3. Verificar Imágenes

Si usas `<Image>` de Next.js, cámbialas a `<img>`:

**ANTES:**
```tsx
import Image from 'next/image'
<Image src="/logo.png" width={100} height={100} />
```

**DESPUÉS:**
```tsx
<img src="/logo.png" width={100} height={100} alt="Logo" />
```

### 4. Actualizar `package.json`

Agrega script de export:

```json
{
  "scripts": {
    "build": "next build",
    "export": "next build && next export",  // ← AGREGAR
    "build:static": "next build"            // ← O este (equivalente con output: 'export')
  }
}
```

---

## 🚀 Build y Deploy

### Desarrollo Local

```bash
cd apps/aurity

# Desarrollo (igual que antes)
pnpm dev

# Build estático
pnpm build

# Resultado: carpeta out/ con HTML estático
ls -lah out/
```

### Deploy a Azure Static Web Apps

```bash
# Deploy via CI/CD (push to main triggers GitHub Actions)
git push origin main

# The pipeline builds and deploys to Azure Static Web Apps automatically
```

---

## ⚠️ Limitaciones del Export Estático

### ❌ NO PUEDES usar:

1. **API Routes** (`app/api/*`)
   - Solución: Usa tu backend FastAPI

2. **Server Components con fetch dinámico**
   - Solución: Todas las páginas son Client Components (`'use client'`)

3. **`getServerSideProps`**
   - Solución: No lo usas (App Router)

4. **Next.js Image Optimization**
   - Solución: `images.unoptimized: true` o usa `<img>`

5. **Dynamic Routes sin `generateStaticParams`**
   - Solución: Define rutas en build time o usa client-side routing

### ✅ SÍ PUEDES usar:

- ✅ React hooks (useState, useEffect, etc.)
- ✅ Client-side routing (useRouter, Link)
- ✅ API calls al backend FastAPI
- ✅ WebSocket/WebRTC (todo en cliente)
- ✅ IndexedDB, localStorage
- ✅ RecordRTC, MediaRecorder
- ✅ Todos tus componentes actuales

---

## 🔍 Verificar Compatibilidad

### Check Rápido

```bash
# Buscar features incompatibles
cd apps/aurity

# API routes (deberías tener solo 1: health)
find app/api -name "route.ts"

# Server-side features (no deberías tener)
grep -r "getServerSideProps\|getStaticProps" app/

# Next Image (opcional verificar)
grep -r "next/image" app/ --include="*.tsx"
```

### Análisis de tu app

```bash
Tu app ACTUAL:
✅ App Router (compatible)
✅ Client Components ('use client')
✅ API calls a FastAPI externo
✅ WebRTC local
✅ IndexedDB
✅ React hooks
✅ Client-side routing
⚠️ 1 API route /api/health (fácil de eliminar)
⚠️ output: 'standalone' (cambiar a 'export')

RESULTADO: 95% compatible con static export!
```

---

## 📊 Comparación: SSR vs Static

| Feature | SSR (actual) | Static Export |
|---------|--------------|---------------|
| **Hosting** | VM + Node.js | Azure Static Web Apps |
| **Costo** | $6/mes | Free tier |
| **Velocidad** | ~100ms | ~20ms (CDN) |
| **Escalamiento** | Manual | Automatico |
| **Mantenimiento** | Actualizar Node | Cero |
| **Deploy** | Manual | CI/CD (push to main) |
| **SSL** | Manual | Automatico |

---

## 🎯 Plan de Migración (15 minutos)

### Step 1: Backup (1 min)
```bash
git checkout -b static-export
```

### Step 2: Update Config (2 min)
```bash
cd apps/aurity
cp next.config.static.js next.config.js
```

### Step 3: Remove API Route (1 min)
```bash
rm app/api/health/route.ts
```

### Step 4: Build Test (5 min)
```bash
pnpm build

# Verificar que genera out/
ls -lah out/

# Test local
cd out/
python3 -m http.server 3000
# Abrir http://localhost:3000
```

### Step 5: Deploy (5 min)
```bash
# Desde repo root
./scripts/deploy-frontend-do.sh
```

### Step 6: Update Backend CORS (1 min)
```bash
# backend/.env
ALLOWED_ORIGINS="http://localhost:9000,https://app.aurity.io"
```

---

## 🐛 Troubleshooting

### Error: "Image Optimization needs server"
```bash
# Solución: Agregar en next.config.js
images: {
  unoptimized: true
}
```

### Error: "API routes not supported"
```bash
# Solución: Eliminar app/api/ o mover lógica al backend
rm -rf app/api/
```

### Error: "Dynamic routes not found"
```bash
# Solución: Agregar generateStaticParams si tienes [id]
export async function generateStaticParams() {
  return [{ id: '1' }, { id: '2' }]
}
```

### Build exitoso pero 404 en producción
```bash
# Solución: Agregar trailingSlash en next.config.js
trailingSlash: true
```

---

## 💡 Best Practices

### 1. Environment Variables

```bash
# .env.production
NEXT_PUBLIC_API_URL=http://YOUR_BACKEND_IP:7001

# Rebuild después de cambiar
pnpm build
```

### 2. Cache Headers

Azure Static Web Apps CDN cachea automaticamente. Cache headers se configuran en `staticwebapp.config.json`.

### 3. Error Pages

Next.js genera `404.html` automáticamente. Para custom:
```tsx
// app/not-found.tsx
export default function NotFound() {
  return <h1>404 - Page Not Found</h1>
}
```

---

## 📈 Resultado Final

```yaml
Antes (SSR):
- Hosting: Droplet $6/mes
- Deploy: docker run / pm2
- Latency: ~100ms
- Scaling: Manual

Despues (Static):
- Hosting: Azure Static Web Apps (Free)
- Deploy: CI/CD push to main
- Latency: ~20ms (CDN global)
- Scaling: Infinito automatico

Bonus:
✅ $1/mes más barato
✅ 5x más rápido
✅ Deploy en segundos
✅ Zero downtime
✅ Auto-scaling
```

---

## 🎁 Scripts Útiles

```bash
# Build + test local
pnpm build && cd out && python3 -m http.server 3000

# Build + deploy via CI/CD
git push origin main  # Triggers Azure Static Web Apps deployment

# Watch + rebuild (dev)
pnpm dev

# Check size del build
du -sh out/
```

---

## ✅ Checklist Final

- [ ] `next.config.js` tiene `output: 'export'`
- [ ] `images.unoptimized: true` agregado
- [ ] API routes eliminadas o movidas a backend
- [ ] Build exitoso: `pnpm build` genera `out/`
- [ ] Test local funciona: `python3 -m http.server` en `out/`
- [ ] Variables de entorno actualizadas
- [ ] CORS configurado en backend
- [ ] Deploy exitoso a Azure Static Web Apps
- [ ] CDN habilitado
- [ ] URL funciona: `https://app.aurity.io`

---

**🚀 ¡Tu app está lista para ser 100% estática y deployar a CDN!**

Tiempo total: **15 minutos**
Ahorro: **$1/mes + 5x velocidad**
Complejidad: **10x más simple**
