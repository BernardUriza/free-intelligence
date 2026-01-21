#!/bin/bash
# Script para descargar el ejecutable de Windows del último build exitoso

set -e

BUILD_ID=${1:-latest}

if [ "$BUILD_ID" = "latest" ]; then
  echo "🔍 Buscando último build exitoso..."
  BUILD_ID=$(gh run list --workflow=build-desktop.yml --branch dev --status success --limit 1 --json databaseId --jq '.[0].databaseId')

  if [ -z "$BUILD_ID" ]; then
    echo "❌ No se encontró ningún build exitoso"
    exit 1
  fi

  echo "✅ Build encontrado: #$BUILD_ID"
fi

echo "📥 Descargando artifacts del build #$BUILD_ID..."

# Create download directory
DOWNLOAD_DIR="downloads/build-$BUILD_ID"
mkdir -p "$DOWNLOAD_DIR"

# Download Windows NSIS installer
echo "Descargando instalador Windows..."
gh run download "$BUILD_ID" --name aurity-windows-nsis --dir "$DOWNLOAD_DIR"

# Download signature (if exists)
echo "Descargando signature..."
gh run download "$BUILD_ID" --name aurity-windows-nsis-sig --dir "$DOWNLOAD_DIR" 2>/dev/null || echo "⚠️  Signature no disponible (OK si build falló en signing)"

# List downloaded files
echo ""
echo "✅ Archivos descargados:"
ls -lh "$DOWNLOAD_DIR"

echo ""
echo "📦 Instalador disponible en:"
echo "   $DOWNLOAD_DIR"

# Get file info
if ls "$DOWNLOAD_DIR"/*.exe 1> /dev/null 2>&1; then
  NSIS_FILE=$(ls "$DOWNLOAD_DIR"/*.exe | head -1)
  FILE_SIZE=$(du -h "$NSIS_FILE" | cut -f1)
  echo ""
  echo "📊 Tamaño: $FILE_SIZE"
  echo "🔗 Archivo: $(basename "$NSIS_FILE")"
fi

echo ""
echo "🚀 Para instalar:"
echo "   1. Ejecuta el instalador .exe"
echo "   2. Click 'More info' → 'Run anyway' en SmartScreen warning"
