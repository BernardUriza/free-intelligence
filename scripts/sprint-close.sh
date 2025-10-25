#!/bin/bash
#
# Free Intelligence - Sprint Close & Backup
# Ejecutar al finalizar cada sprint (15 días)
#
# Uso: ./scripts/sprint-close.sh SPR-2025W43 [DRY_RUN|EXECUTE]
#

set -e

SPRINT_LABEL="${1:-SPR-UNKNOWN}"
MODE="${2:-DRY_RUN}"
TIMEZONE="America/Mexico_City"
REPO_ROOT="$(git rev-parse --show-toplevel)"
BACKUP_DIR="$REPO_ROOT/backups"
CLAUDE_MD="$REPO_ROOT/claude.md"

# Fecha actual en timezone local
CURRENT_DATE=$(TZ=$TIMEZONE date '+%Y-%m-%d')
CURRENT_TIME=$(TZ=$TIMEZONE date '+%H:%M')
TIMESTAMP=$(TZ=$TIMEZONE date '+%Y-%m-%d %H:%M')

echo "🎯 Sprint Close - $SPRINT_LABEL"
echo "Mode: $MODE"
echo "Timestamp: $TIMESTAMP ($TIMEZONE)"
echo ""

# 1. Determinar versión
echo "📌 Step 1: Determinando versión..."
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
echo "  Último tag: $LAST_TAG"

# Contar commits desde último tag
COMMITS_SINCE=$(git rev-list ${LAST_TAG}..HEAD --count 2>/dev/null || git rev-list HEAD --count)
echo "  Commits desde tag: $COMMITS_SINCE"

if [ "$COMMITS_SINCE" -gt 0 ]; then
    # Hay cambios, incrementar versión
    # Extraer números de versión
    MAJOR=$(echo $LAST_TAG | sed 's/v\([0-9]*\)\..*/\1/')
    MINOR=$(echo $LAST_TAG | sed 's/v[0-9]*\.\([0-9]*\)\..*/\1/')
    PATCH=$(echo $LAST_TAG | sed 's/v[0-9]*\.[0-9]*\.\([0-9]*\)/\1/')

    # Incrementar MINOR para sprints (cada 15 días = minor release)
    MINOR=$((MINOR + 1))
    NEW_TAG="v${MAJOR}.${MINOR}.0"
else
    NEW_TAG=$LAST_TAG
fi

echo "  Nueva versión: $NEW_TAG"
echo ""

# 2. Generar notas de versión
echo "📝 Step 2: Generando notas de versión..."
RELEASE_NOTES_FILE="$BACKUP_DIR/release-notes-${NEW_TAG}.md"

if [ "$COMMITS_SINCE" -gt 0 ]; then
    cat > "$RELEASE_NOTES_FILE" << EOF
# Release Notes - $NEW_TAG

**Sprint**: $SPRINT_LABEL
**Fecha**: $CURRENT_DATE
**Commits**: $COMMITS_SINCE desde $LAST_TAG

## Cambios

$(git log ${LAST_TAG}..HEAD --pretty=format:"- %s (%h)" --no-merges 2>/dev/null || git log --pretty=format:"- %s (%h)" --no-merges)

## Áreas Afectadas

$(git log ${LAST_TAG}..HEAD --name-only --pretty=format:"" 2>/dev/null | sort -u | grep -v '^$' | head -20 || echo "- Archivos iniciales")

## Estadísticas

- Total commits: $COMMITS_SINCE
- Archivos modificados: $(git diff --name-only ${LAST_TAG}..HEAD 2>/dev/null | wc -l || echo "N/A")

EOF
else
    cat > "$RELEASE_NOTES_FILE" << EOF
# Release Notes - $NEW_TAG

**Sprint**: $SPRINT_LABEL
**Fecha**: $CURRENT_DATE
**Estado**: Sin cambios desde $LAST_TAG

EOF
fi

echo "  Notas guardadas en: $RELEASE_NOTES_FILE"
cat "$RELEASE_NOTES_FILE"
echo ""

# 3. Crear tag (solo en EXECUTE)
if [ "$MODE" = "EXECUTE" ] && [ "$COMMITS_SINCE" -gt 0 ]; then
    echo "🏷️  Step 3: Creando tag $NEW_TAG..."
    git tag -a "$NEW_TAG" -m "Sprint $SPRINT_LABEL - $(date '+%Y-%m-%d')"
    echo "  Tag $NEW_TAG creado ✅"
else
    echo "🏷️  Step 3: Tag $NEW_TAG (SIMULADO - modo $MODE)"
fi
echo ""

# 4. Crear bundle backup
echo "💾 Step 4: Generando bundle backup..."
BUNDLE_NAME="fi-${SPRINT_LABEL}-${NEW_TAG}-${CURRENT_DATE}.bundle"
BUNDLE_PATH="$BACKUP_DIR/$BUNDLE_NAME"
SHA256_PATH="$BACKUP_DIR/${SPRINT_LABEL}-${NEW_TAG}.sha256"

if [ "$MODE" = "EXECUTE" ]; then
    git bundle create "$BUNDLE_PATH" --all
    BUNDLE_SIZE=$(ls -lh "$BUNDLE_PATH" | awk '{print $5}')
    echo "  Bundle creado: $BUNDLE_PATH ($BUNDLE_SIZE)"

    # Calcular SHA256
    shasum -a 256 "$BUNDLE_PATH" | awk '{print $1}' > "$SHA256_PATH"
    BUNDLE_SHA=$(cat "$SHA256_PATH")
    echo "  SHA256: $BUNDLE_SHA"
    echo "  SHA256 guardado en: $SHA256_PATH"
else
    echo "  Bundle: $BUNDLE_PATH (SIMULADO)"
    BUNDLE_SIZE="N/A"
    BUNDLE_SHA="SIMULADO"
fi
echo ""

# 5. Retención (mantener últimos 12 bundles)
echo "🗑️  Step 5: Aplicando retención (últimos 12 bundles)..."
BUNDLE_COUNT=$(ls -1 "$BACKUP_DIR"/*.bundle 2>/dev/null | wc -l || echo 0)
echo "  Bundles actuales: $BUNDLE_COUNT"

if [ "$BUNDLE_COUNT" -gt 12 ] && [ "$MODE" = "EXECUTE" ]; then
    # Eliminar los más antiguos
    ls -1t "$BACKUP_DIR"/*.bundle | tail -n +13 | while read old_bundle; do
        echo "  Eliminando: $old_bundle"
        rm -f "$old_bundle"
        rm -f "${old_bundle%.bundle}.sha256" 2>/dev/null || true
    done
    echo "  Retención aplicada ✅"
else
    echo "  Retención: No necesaria (< 12 bundles)"
fi
echo ""

# 6. Actualizar claude.md
echo "📖 Step 6: Actualizando claude.md..."

TARJETAS_CERRADAS=$(grep -c "Estado.*Done" "$CLAUDE_MD" 2>/dev/null || echo 0)
ENTRADAS_SPRINT=$(grep -c "\[$SPRINT_LABEL\]" "$CLAUDE_MD" 2>/dev/null || echo 0)

CIERRE_ENTRY=$(cat << EOF

---

## [$TIMESTAMP] $SPRINT_LABEL — CIERRE DE SPRINT
Estado: Sprint Activo → Sprint Cerrado | Tag: $NEW_TAG
Fechas: Sprint completo (15 días)
Acción: Cierre de sprint y generación de backup
Síntesis técnica:
- Tag $NEW_TAG creado ($COMMITS_SINCE commits desde $LAST_TAG)
- Backup generado: $BUNDLE_NAME ($BUNDLE_SIZE)
- SHA256: $BUNDLE_SHA
- Retención aplicada: manteniendo últimos 12 bundles
- Notas de versión: $RELEASE_NOTES_FILE

Métricas del sprint:
- Tarjetas cerradas: $TARJETAS_CERRADAS
- Entradas en bitácora: $ENTRADAS_SPRINT
- Commits totales: $COMMITS_SINCE

Verificación:
- Tag existe: $(git tag -l "$NEW_TAG" | wc -l | xargs)
- Bundle existe: $([ -f "$BUNDLE_PATH" ] && echo "✅" || echo "⏸️ (modo $MODE)")
- SHA256 existe: $([ -f "$SHA256_PATH" ] && echo "✅" || echo "⏸️ (modo $MODE)")
- Bundle size: $BUNDLE_SIZE
- Entradas añadidas en sprint: $ENTRADAS_SPRINT

Próximo paso: Iniciar siguiente sprint con nueva planificación

---

EOF
)

if [ "$MODE" = "EXECUTE" ]; then
    echo "$CIERRE_ENTRY" >> "$CLAUDE_MD"
    echo "  Entrada de cierre agregada a claude.md ✅"
else
    echo "  Entrada de cierre (SIMULADA):"
    echo "$CIERRE_ENTRY" | head -20
fi
echo ""

# 7. Resumen final
echo "✅ RESUMEN FINAL"
echo "================"
echo "Modo: $MODE"
echo "Sprint: $SPRINT_LABEL"
echo "Tag: $NEW_TAG (commits: $COMMITS_SINCE)"
echo "Bundle: $BUNDLE_NAME"
echo "SHA256: $(echo $BUNDLE_SHA | cut -c1-16)..."
echo "Backup path: $BUNDLE_PATH"
echo "Entradas claude.md: $ENTRADAS_SPRINT"
echo ""

if [ "$MODE" = "DRY_RUN" ]; then
    echo "⚠️  MODO DRY_RUN: No se aplicaron cambios"
    echo "   Ejecutar con: ./scripts/sprint-close.sh $SPRINT_LABEL EXECUTE"
else
    echo "✅ Sprint cerrado exitosamente"
fi
