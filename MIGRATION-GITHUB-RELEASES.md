# Migración: Azure Blob → GitHub Releases

Este documento describe la migración de distribución de instaladores desde Azure Blob Storage a GitHub Releases.

## Estado Actual (Antes)

```
┌─────────────────────────────────────┐
│ Azure Blob Storage (CDN)            │
│ • URLs hardcoded en page.tsx       │
│ • Upload manual                     │
│ • macOS ✅                          │
│ • Linux ✅                          │
│ • Windows ❌                        │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ /downloads page                     │
│ • URLs estáticas                    │
│ • Requiere update manual            │
└─────────────────────────────────────┘
```

## Estado Futuro (Después)

```
┌─────────────────────────────────────┐
│ GitHub Actions CI/CD                │
│ • Auto-build 3 plataformas          │
│ • Auto-sign con Ed25519             │
│ • Auto-upload a GitHub Releases     │
│ • Auto-generate updater manifest    │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ GitHub Releases (source of truth)   │
│ • macOS ✅                          │
│ • Linux ✅                          │
│ • Windows ✅                        │
│ • Versionado automático             │
└─────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌───────────────┐   ┌──────────────────┐
│ /downloads    │   │ App Auto-Updater │
│ (GitHub API)  │   │ (background)     │
└───────────────┘   └──────────────────┘
```

---

## Pasos de Migración

### ✅ Fase 1: Fix CI/CD Windows (COMPLETADO en este PR)

**Archivos modificados:**
- `apps/aurity-desktop/src-tauri/tauri.conf.json` → Platform-specific binaries
- `apps/aurity-desktop/scripts/set-version.js` → Versionado dinámico
- `.github/workflows/build-desktop.yml` → Fixes Windows build

**Resultado:**
- ✅ Windows build funciona
- ✅ Artifacts en GitHub Actions
- ✅ Descargable con `gh run download`

---

### ⏭️ Fase 2: Migrar `/downloads` a GitHub API (MANUAL)

**Pasos:**

1. **Backup del archivo original:**
   ```bash
   cd apps/aurity/app/downloads
   cp page.tsx page.tsx.backup
   ```

2. **Reemplazar con versión dinámica:**
   ```bash
   cp page-dynamic.tsx.new page.tsx
   ```

3. **Verificar localmente:**
   ```bash
   cd apps/aurity
   pnpm dev
   # Abrir http://localhost:9000/downloads
   ```

4. **Verificar que muestra 3 plataformas:**
   - macOS (DMG)
   - Linux (AppImage)
   - Windows (NSIS) ← NUEVO

5. **Commit cambios:**
   ```bash
   git add apps/aurity/app/downloads/page.tsx
   git commit -m "feat(downloads): migrate to GitHub API (dynamic releases)"
   ```

**Archivos involucrados:**
- `apps/aurity/app/downloads/page.tsx` → Reemplazar con GitHub API fetch
- `apps/aurity/app/downloads/page-dynamic.tsx.new` → Nueva versión (template)

---

### ⏭️ Fase 3: Limpiar Azure Blob Storage (OPCIONAL)

**IMPORTANTE:** Solo hacer esto DESPUÉS de verificar que `/downloads` funciona con GitHub API.

**Pasos:**

1. **Dry-run (listar archivos sin borrar):**
   ```bash
   chmod +x scripts/cleanup-azure-blob.sh
   ./scripts/cleanup-azure-blob.sh
   ```

2. **Verificar que archivos se pueden eliminar:**
   - `Aurity_1.0.0_aarch64.dmg` (96 MB)
   - `Aurity_1.0.0_amd64.AppImage` (201 MB)

3. **Eliminar archivos:**
   ```bash
   ./scripts/cleanup-azure-blob.sh --delete
   # Confirmar con 'yes'
   ```

4. **Verificar que `/downloads` sigue funcionando:**
   - URLs ahora vienen de GitHub Releases
   - No más Azure Blob Storage

**Costo savings:**
- Azure Blob Storage: ~$0.02/GB/mes → $0/mes (si eliminas la cuenta completa)
- GitHub Releases: Gratis (hasta 2 GB por archivo)

---

## Verificación End-to-End

### 1. Trigger build Windows

```bash
gh workflow run build-desktop.yml -f platform=windows
gh run watch
```

### 2. Verificar GitHub Release

```bash
# Listar releases
gh release list

# Descargar último release
gh release download v0.0.0-abc1234 --pattern "*.nsis.zip"
```

### 3. Verificar `/downloads` page

```bash
# Local
curl -s http://localhost:9000/downloads | grep "Download v0.0.0"

# Producción (después de deploy)
curl -s https://app.aurity.io/downloads | grep "Download v0.0.0"
```

### 4. Verificar auto-updater (desktop app)

```bash
# Desde la app de escritorio
# Check for updates → debe detectar nueva versión
# Download and install → debe descargar desde GitHub Releases
```

---

## Rollback Plan

Si algo falla:

### Revertir `/downloads` a Azure Blob:

```bash
cd apps/aurity/app/downloads
cp page.tsx.backup page.tsx
git checkout HEAD -- page.tsx
```

### Revertir CI/CD fixes:

```bash
git checkout HEAD~1 -- .github/workflows/build-desktop.yml
git checkout HEAD~1 -- apps/aurity-desktop/src-tauri/tauri.conf.json
```

---

## FAQs

### ¿Por qué GitHub Releases en vez de Azure Blob?

**Pros:**
- ✅ Automático desde CI/CD (cero manual work)
- ✅ Versionado completo (tags, changelog)
- ✅ Gratis (hasta 2 GB por archivo)
- ✅ Un solo source of truth

**Contras:**
- ⚠️ URLs largas (se puede mitigar con short URLs)
- ⚠️ Requiere autenticación para repos privados

### ¿Qué pasa con Azure Blob?

- Puedes dejarlo como está (no afecta nada)
- O eliminarlo con `cleanup-azure-blob.sh --delete`
- `/downloads` ya no leerá de ahí después de Fase 2

### ¿El auto-updater seguirá funcionando?

Sí, el auto-updater YA está configurado para leer de GitHub Releases:

```json
// apps/aurity-desktop/src-tauri/tauri.conf.json
"updater": {
  "endpoints": [
    "https://github.com/BernardUriza/free-intelligence/releases/latest/download/aurity-desktop-updater.json"
  ]
}
```

El workflow ya genera el manifest (`generate-manifest` job).

---

## Siguiente Paso

**Para continuar con la implementación:**

1. ✅ Review este PR (Fix CI/CD Windows)
2. ⏭️ Después de merge: Seguir Fase 2 (migrar `/downloads`)
3. ⏭️ Opcional: Fase 3 (limpiar Azure)

**Cualquier duda, pregunta antes de ejecutar los comandos de delete.**
