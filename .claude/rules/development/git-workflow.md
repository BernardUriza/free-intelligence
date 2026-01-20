# Git Workflow (2-Branch Model)

## Ramas Permitidas

```
SOLO ESTAS DOS RAMAS:
  • dev  → Desarrollo activo (multi-feature, multi-agent)
  • main → Producción (protegida, requiere PR + CI)
```

## Flujo de Trabajo

```
┌─────────────────────────────────────┐
│              dev                     │
│  Trabajas aquí (caos controlado)    │
│  CI corre en cada push              │
└──────────────┬──────────────────────┘
               │ PR cuando esté listo
               ▼
┌─────────────────────────────────────┐
│              main                    │
│  Producción (protegida)             │
│  Requiere: PR + CI pasando          │
└─────────────────────────────────────┘
```

## Comandos Diarios

```bash
git checkout dev                    # Siempre trabajar en dev
git add . && git commit -m "..."    # Commits frecuentes
git push origin dev                 # CI valida automáticamente
```

## ⚠️ Sincronización Crítica

Cuando un PR se mergea a main, dev queda BEHIND. **SIEMPRE sincronizar**:

```bash
git checkout dev
git fetch origin
git merge origin/main -m "chore: sync dev with main after PR #XX merge"
git push origin dev

# Verificar que dev está actualizado
git log origin/main..origin/dev    # Debe estar vacío después de sync
```

**Problema:** Si no sincronizas, los PRs quedarán en estado "BEHIND" y no podrán mergearse  
**Solución:** Sincronizar dev con main después de CADA merge

## Deploy a Producción

```bash
gh pr create --base main --head dev --title "Release: descripción"
# Esperar CI ✅ → Merge → Deploy automático via CD
```

## Reglas para Claude

❌ **NUNCA:**
- Crear ramas adicionales (no feature branches)
- Pushear directo a main
- Bypass de PR review

✅ **SIEMPRE:**
- Trabajar en dev
- Usar PR para subir a main
- Verificar que CI pase antes de merge
- **CRÍTICO:** Sincronizar dev con main después de CADA merge

## Optimización: No necesitas main local

Este workflow usa 2 branches REMOTAS (origin/dev, origin/main) pero solo necesitas 1 branch LOCAL (dev).

**Beneficios de borrar main local:**
- ✅ Imposible commitear accidentalmente a main
- ✅ origin/main siempre es truth source
- ✅ Menos confusión mental
- ✅ git diff origin/main..dev funciona igual

**Cómo borrar main local:**
```bash
git checkout dev
git branch -D main  # Safe, no afecta remoto
```

Después de borrar, el workflow es idéntico:
```bash
git fetch origin                    # Actualizar referencias remotas
git merge origin/main               # Sincronizar desde remoto
git diff origin/main..dev           # Comparar con remoto
```
