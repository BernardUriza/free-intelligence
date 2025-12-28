#!/bin/bash
# ============================================================================
# AURITY Ollama Tunnel Manager
# ============================================================================
# Inicia Cloudflare Tunnel para exponer Ollama local y actualiza DO backend
#
# Uso:
#   ./scripts/ollama-tunnel.sh start    # Inicia tunnel y actualiza DO
#   ./scripts/ollama-tunnel.sh stop     # Detiene tunnel
#   ./scripts/ollama-tunnel.sh status   # Muestra estado actual
#   ./scripts/ollama-tunnel.sh url      # Muestra URL actual
# ============================================================================

set -e

# Configuración
TUNNEL_LOG="/tmp/ollama-tunnel.log"
TUNNEL_URL_FILE="/tmp/ollama-tunnel-url.txt"
DO_HOST="root@104.131.175.65"
OLLAMA_PORT="11434"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() { echo -e "${BLUE}[TUNNEL]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

# Verificar dependencias
check_deps() {
    command -v cloudflared >/dev/null 2>&1 || { error "cloudflared no instalado. Run: brew install cloudflared"; exit 1; }
    command -v ollama >/dev/null 2>&1 || { error "ollama no instalado"; exit 1; }
    command -v jq >/dev/null 2>&1 || { error "jq no instalado. Run: brew install jq"; exit 1; }
}

# Iniciar Ollama con CORS habilitado
start_ollama() {
    log "Verificando Ollama..."

    if curl -s http://localhost:$OLLAMA_PORT/api/tags >/dev/null 2>&1; then
        success "Ollama ya está corriendo"
    else
        log "Iniciando Ollama con CORS habilitado..."
        export OLLAMA_ORIGINS="*"
        export OLLAMA_HOST="0.0.0.0:$OLLAMA_PORT"
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        sleep 5

        if curl -s http://localhost:$OLLAMA_PORT/api/tags >/dev/null 2>&1; then
            success "Ollama iniciado"
        else
            error "No se pudo iniciar Ollama"
            exit 1
        fi
    fi
}

# Iniciar Cloudflare Tunnel
start_tunnel() {
    log "Iniciando Cloudflare Tunnel..."

    # Matar tunnel anterior si existe
    pkill -f "cloudflared tunnel" 2>/dev/null || true
    sleep 2

    # Iniciar tunnel y capturar salida
    cloudflared tunnel --url http://localhost:$OLLAMA_PORT > "$TUNNEL_LOG" 2>&1 &
    TUNNEL_PID=$!
    echo $TUNNEL_PID > /tmp/ollama-tunnel.pid

    log "Esperando URL del tunnel (PID: $TUNNEL_PID)..."

    # Esperar hasta 30 segundos por la URL
    for i in {1..30}; do
        if grep -q "trycloudflare.com" "$TUNNEL_LOG" 2>/dev/null; then
            TUNNEL_URL=$(grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' "$TUNNEL_LOG" | head -1)
            echo "$TUNNEL_URL" > "$TUNNEL_URL_FILE"
            success "Tunnel activo: $TUNNEL_URL"
            return 0
        fi
        sleep 1
    done

    error "Timeout esperando URL del tunnel"
    cat "$TUNNEL_LOG"
    exit 1
}

# Actualizar configuración en Digital Ocean
update_do() {
    local url=$1
    log "Actualizando Digital Ocean backend..."

    # Verificar conexión SSH
    if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$DO_HOST" "echo ok" >/dev/null 2>&1; then
        error "No se puede conectar a DO via SSH"
        return 1
    fi

    # Actualizar y reiniciar backend
    ssh "$DO_HOST" bash << EOF
# Matar backend actual
pkill -9 -f uvicorn 2>/dev/null || true
sleep 2

# Iniciar con nueva URL de Ollama
cd /opt/free-intelligence
export PYTHONPATH=.
export PYTHONNOUSERSITE=1
export OLLAMA_HOST="$url"

# Escribir la URL a un archivo para persistencia
echo "$url" > /tmp/ollama-tunnel-url.txt

# Iniciar backend
nohup python3.14 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 7001 > /tmp/backend.log 2>&1 &

sleep 10

# Verificar
if curl -s http://localhost:7001/api/health | grep -q ok; then
    echo "Backend reiniciado con OLLAMA_HOST=$url"
else
    echo "Error: Backend no respondió"
    tail -20 /tmp/backend.log
    exit 1
fi
EOF

    success "DO actualizado con OLLAMA_HOST=$url"
}

# Guardar URL en GitHub Secret (opcional)
update_github_secret() {
    local url=$1
    log "Actualizando GitHub Secret..."

    if command -v gh >/dev/null 2>&1; then
        echo "$url" | gh secret set OLLAMA_TUNNEL_URL --repo="$(git remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]\(.*\)\.git/\1/')" 2>/dev/null && \
            success "GitHub Secret OLLAMA_TUNNEL_URL actualizado" || \
            warn "No se pudo actualizar GitHub Secret (opcional)"
    else
        warn "gh CLI no disponible, saltando actualización de secret"
    fi
}

# Probar conexión end-to-end
test_connection() {
    local url=$1
    log "Probando conexión end-to-end..."

    # Test 1: Tunnel -> Ollama local
    log "Test 1: Tunnel -> Ollama"
    if curl -s -m 10 "$url/api/tags" | jq -e '.models[0].name' >/dev/null 2>&1; then
        success "Tunnel -> Ollama: OK"
    else
        error "Tunnel -> Ollama: FAILED"
        return 1
    fi

    # Test 2: DO -> Tunnel -> Ollama
    log "Test 2: DO Backend -> Tunnel -> Ollama"
    CHAT_RESPONSE=$(curl -s -m 60 -X POST "https://app.aurity.io/api/workflows/aurity/assistant/chat" \
        -H "Content-Type: application/json" \
        -d '{"messages":[{"role":"user","content":"di hola"}],"persona":"general_assistant"}' 2>/dev/null)

    if echo "$CHAT_RESPONSE" | jq -e '.content or .message' >/dev/null 2>&1; then
        success "DO -> Tunnel -> Ollama: OK"
        echo "$CHAT_RESPONSE" | jq -r '.content // .message.content // "Response received"' | head -c 100
        echo ""
    else
        warn "DO -> Tunnel -> Ollama: Sin respuesta (puede tardar en propagarse)"
    fi
}

# Detener tunnel
stop_tunnel() {
    log "Deteniendo tunnel..."
    pkill -f "cloudflared tunnel" 2>/dev/null || true
    rm -f /tmp/ollama-tunnel.pid "$TUNNEL_URL_FILE"
    success "Tunnel detenido"
}

# Mostrar estado
show_status() {
    echo ""
    echo "=== AURITY Ollama Tunnel Status ==="
    echo ""

    # Ollama
    if curl -s http://localhost:$OLLAMA_PORT/api/tags >/dev/null 2>&1; then
        echo -e "Ollama:    ${GREEN}Running${NC} (localhost:$OLLAMA_PORT)"
    else
        echo -e "Ollama:    ${RED}Stopped${NC}"
    fi

    # Tunnel
    if pgrep -f "cloudflared tunnel" >/dev/null 2>&1; then
        if [ -f "$TUNNEL_URL_FILE" ]; then
            echo -e "Tunnel:    ${GREEN}Running${NC} ($(cat $TUNNEL_URL_FILE))"
        else
            echo -e "Tunnel:    ${YELLOW}Running${NC} (URL desconocida)"
        fi
    else
        echo -e "Tunnel:    ${RED}Stopped${NC}"
    fi

    # DO Backend
    if curl -s -m 5 https://app.aurity.io/api/health | grep -q ok 2>/dev/null; then
        echo -e "DO Backend: ${GREEN}Running${NC}"
    else
        echo -e "DO Backend: ${RED}Not responding${NC}"
    fi

    echo ""
}

# Mostrar URL actual
show_url() {
    if [ -f "$TUNNEL_URL_FILE" ]; then
        cat "$TUNNEL_URL_FILE"
    else
        error "No hay tunnel activo"
        exit 1
    fi
}

# Main
case "${1:-start}" in
    start)
        check_deps
        start_ollama
        start_tunnel
        TUNNEL_URL=$(cat "$TUNNEL_URL_FILE")
        update_do "$TUNNEL_URL"
        update_github_secret "$TUNNEL_URL"
        test_connection "$TUNNEL_URL"
        echo ""
        success "=== Tunnel configurado ==="
        echo "URL: $TUNNEL_URL"
        echo ""
        echo "Para monitorear: tail -f $TUNNEL_LOG"
        echo "Para detener:    $0 stop"
        ;;
    stop)
        stop_tunnel
        ;;
    status)
        show_status
        ;;
    url)
        show_url
        ;;
    restart)
        stop_tunnel
        sleep 2
        exec "$0" start
        ;;
    *)
        echo "Uso: $0 {start|stop|status|url|restart}"
        exit 1
        ;;
esac
