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
#   ./scripts/ollama-tunnel.sh monitor  # Monitor interactivo (UI bonita)
#   ./scripts/ollama-tunnel.sh url      # Muestra URL actual
#   ./scripts/ollama-tunnel.sh restart  # Reinicia tunnel
#
# Monitor interactivo:
#   [Q] Quit      - Salir del monitor
#   [R] Restart   - Reiniciar tunnel
#   [T] Test LLM  - Probar conexión con curl al LLM
#   [C] Copy URL  - Copiar URL al clipboard
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

# Mostrar estado (simple)
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

# ============================================================================
# INTERACTIVE MONITOR MODE
# ============================================================================

# Get terminal width
get_term_width() {
    local width
    if [ -n "$COLUMNS" ]; then
        width=$COLUMNS
    elif command -v tput >/dev/null 2>&1; then
        width=$(tput cols 2>/dev/null || echo 80)
    else
        width=80
    fi
    # Minimum 60, maximum 120 for readability
    [ "$width" -lt 60 ] && width=60
    [ "$width" -gt 120 ] && width=120
    echo "$width"
}

# Get active model info
get_model_info() {
    local model_data
    model_data=$(curl -s -m 3 http://localhost:$OLLAMA_PORT/api/ps 2>/dev/null)
    if [ -n "$model_data" ] && echo "$model_data" | jq -e '.models[0]' >/dev/null 2>&1; then
        local name size_bytes size_gb
        name=$(echo "$model_data" | jq -r '.models[0].name // "none"')
        size_bytes=$(echo "$model_data" | jq -r '.models[0].size // 0')
        size_gb=$(echo "scale=1; $size_bytes / 1073741824" | bc 2>/dev/null || echo "?")
        echo "$name|${size_gb} GB loaded"
    else
        # No model loaded, get available models
        local models
        models=$(curl -s -m 3 http://localhost:$OLLAMA_PORT/api/tags 2>/dev/null | jq -r '.models[0].name // "none"')
        echo "$models|not loaded"
    fi
}

# Measure tunnel latency
get_tunnel_latency() {
    local url=$1
    if [ -z "$url" ]; then
        echo "N/A"
        return
    fi
    local start end latency
    start=$(date +%s%N 2>/dev/null || echo "0")
    if curl -s -m 5 -o /dev/null "$url/api/tags" 2>/dev/null; then
        end=$(date +%s%N 2>/dev/null || echo "0")
        if [ "$start" != "0" ] && [ "$end" != "0" ]; then
            latency=$(( (end - start) / 1000000 ))
            echo "${latency}ms"
        else
            echo "OK"
        fi
    else
        echo "FAIL"
    fi
}

# Run LLM test
run_llm_test() {
    local url=$1
    echo ""
    echo -e "${BLUE}Running LLM test...${NC}"
    local start end response time_ms
    start=$(date +%s%N 2>/dev/null || echo "0")
    response=$(curl -s -m 30 "$url/api/chat" -d '{
        "model": "qwen3:1.7b",
        "messages": [{"role": "user", "content": "Say hello in 5 words"}],
        "think": false,
        "stream": false
    }' 2>/dev/null)
    end=$(date +%s%N 2>/dev/null || echo "0")

    if [ "$start" != "0" ] && [ "$end" != "0" ]; then
        time_ms=$(( (end - start) / 1000000 ))
    else
        time_ms="?"
    fi

    if echo "$response" | jq -e '.message.content' >/dev/null 2>&1; then
        local content
        content=$(echo "$response" | jq -r '.message.content' | head -c 100)
        echo -e "${GREEN}[OK]${NC} Response in ${time_ms}ms: $content"
    else
        echo -e "${RED}[FAIL]${NC} No response or error"
        echo "$response" | head -c 200
    fi
    echo ""
    echo "Press any key to continue..."
    read -rsn1
}

# Copy URL to clipboard
copy_url() {
    local url=$1
    if [ -z "$url" ]; then
        echo -e "${RED}No URL available${NC}"
        return
    fi
    # Try different clipboard commands
    if command -v pbcopy >/dev/null 2>&1; then
        echo -n "$url" | pbcopy
        echo -e "${GREEN}URL copied to clipboard (pbcopy)${NC}"
    elif command -v xclip >/dev/null 2>&1; then
        echo -n "$url" | xclip -selection clipboard
        echo -e "${GREEN}URL copied to clipboard (xclip)${NC}"
    elif command -v xsel >/dev/null 2>&1; then
        echo -n "$url" | xsel --clipboard
        echo -e "${GREEN}URL copied to clipboard (xsel)${NC}"
    else
        echo -e "${YELLOW}No clipboard tool found. URL: $url${NC}"
    fi
    sleep 1
}

# Draw box line
draw_line() {
    local width=$1 char=$2 left=$3 right=$4
    printf "%s" "$left"
    for ((i=1; i<width-1; i++)); do printf "%s" "$char"; done
    printf "%s\n" "$right"
}

# Pad string to width
pad_string() {
    local str=$1 width=$2
    local len=${#str}
    local spaces=$((width - len))
    printf "%s" "$str"
    for ((i=0; i<spaces; i++)); do printf " "; done
}

# Interactive monitor
show_monitor() {
    local width url tunnel_pid model_info model_name model_status latency current_time
    local ollama_status tunnel_status

    # Hide cursor
    tput civis 2>/dev/null || true
    trap 'tput cnorm 2>/dev/null; exit 0' EXIT INT TERM

    while true; do
        width=$(get_term_width)
        local inner_width=$((width - 4))

        # Gather data
        url=""
        [ -f "$TUNNEL_URL_FILE" ] && url=$(cat "$TUNNEL_URL_FILE" 2>/dev/null)

        tunnel_pid=""
        [ -f /tmp/ollama-tunnel.pid ] && tunnel_pid=$(cat /tmp/ollama-tunnel.pid 2>/dev/null)

        # Check Ollama
        if curl -s -m 2 http://localhost:$OLLAMA_PORT/api/tags >/dev/null 2>&1; then
            ollama_status="${GREEN}● Running${NC}"
        else
            ollama_status="${RED}● Stopped${NC}"
        fi

        # Check tunnel
        if pgrep -f "cloudflared tunnel" >/dev/null 2>&1; then
            tunnel_status="${GREEN}● Running${NC}"
        else
            tunnel_status="${RED}● Stopped${NC}"
        fi

        # Get model info
        model_info=$(get_model_info)
        model_name=$(echo "$model_info" | cut -d'|' -f1)
        model_status=$(echo "$model_info" | cut -d'|' -f2)

        # Get latency (async would be better but keeping simple)
        if [ -n "$url" ]; then
            latency=$(get_tunnel_latency "$url")
            if [ "$latency" = "FAIL" ]; then
                url_status="${RED}● Unreachable${NC}"
            else
                url_status="${GREEN}● Accessible${NC}   Latency: $latency"
            fi
        else
            latency="N/A"
            url_status="${YELLOW}● No URL${NC}"
        fi

        current_time=$(date +"%H:%M:%S")

        # Clear screen and draw
        clear

        # Header
        draw_line "$width" "─" "┌" "┐"
        printf "│  ${BLUE}FI EDGE MONITOR${NC}"
        local header_right="AURITY v0.1.1 │"
        local header_left_len=18  # "  FI EDGE MONITOR" visible length
        local header_right_len=16 # "AURITY v0.1.1 │" length
        local header_spaces=$((width - header_left_len - header_right_len - 2))
        for ((i=0; i<header_spaces; i++)); do printf " "; done
        printf "%s\n" "$header_right"
        draw_line "$width" "─" "├" "┤"

        # Ollama status
        printf "│  OLLAMA   "
        printf "%b    localhost:%s" "$ollama_status" "$OLLAMA_PORT"
        local line1_len=$((11 + 9 + 6 + 10 + ${#OLLAMA_PORT}))  # approximate
        for ((i=line1_len; i<inner_width; i++)); do printf " "; done
        printf " │\n"

        # Model info
        printf "│  MODEL    %-12s (%s)" "$model_name" "$model_status"
        local line2_base=$((10 + 12 + 3 + ${#model_status}))
        for ((i=line2_base; i<inner_width; i++)); do printf " "; done
        printf " │\n"

        # Empty line
        printf "│"
        for ((i=0; i<width-2; i++)); do printf " "; done
        printf "│\n"

        # Tunnel status
        printf "│  TUNNEL   "
        printf "%b    PID: %-6s" "$tunnel_status" "${tunnel_pid:-N/A}"
        local line3_len=$((11 + 9 + 11))
        for ((i=line3_len; i<inner_width; i++)); do printf " "; done
        printf " │\n"

        # URL line (full URL)
        printf "│  URL      "
        if [ -n "$url" ]; then
            local url_display="$url"
            local max_url_len=$((inner_width - 11))
            if [ ${#url} -gt $max_url_len ]; then
                url_display="${url:0:$max_url_len}"
            fi
            printf "%-${max_url_len}s" "$url_display"
        else
            printf "%-$((inner_width - 11))s" "(no tunnel active)"
        fi
        printf " │\n"

        # Status line
        printf "│  STATUS   "
        printf "%b" "$url_status"
        # Calculate remaining space (approximate - ANSI codes make this tricky)
        local status_base=30
        for ((i=status_base; i<inner_width; i++)); do printf " "; done
        printf " │\n"

        # Separator
        draw_line "$width" "─" "├" "┤"

        # Footer with options
        printf "│  [Q] Quit   [R] Restart   [T] Test LLM   [C] Copy URL"
        local footer_left=55
        local footer_right_len=$((8 + 2))  # time + " │"
        local footer_spaces=$((width - footer_left - footer_right_len - 2))
        for ((i=0; i<footer_spaces; i++)); do printf " "; done
        printf "%s │\n" "$current_time"
        draw_line "$width" "─" "└" "┘"

        # Handle input (non-blocking with timeout)
        read -rsn1 -t 2 key 2>/dev/null || key=""
        case "$key" in
            q|Q)
                tput cnorm 2>/dev/null
                echo "Exiting monitor..."
                exit 0
                ;;
            r|R)
                tput cnorm 2>/dev/null
                echo "Restarting tunnel..."
                stop_tunnel
                sleep 2
                exec "$0" start
                ;;
            t|T)
                if [ -n "$url" ]; then
                    run_llm_test "$url"
                else
                    echo -e "${RED}No tunnel URL available${NC}"
                    sleep 2
                fi
                ;;
            c|C)
                copy_url "$url"
                ;;
        esac
    done
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
        echo "Para monitorear: $0 monitor"
        echo "Para detener:    $0 stop"
        ;;
    stop)
        stop_tunnel
        ;;
    status)
        show_status
        ;;
    monitor)
        show_monitor
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
        echo "Uso: $0 {start|stop|status|monitor|url|restart}"
        exit 1
        ;;
esac
