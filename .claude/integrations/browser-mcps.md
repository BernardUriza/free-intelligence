# Browser MCPs (Automatización de Navegador)

## Chrome DevTools MCP

Permite interactuar con Chrome: clicks, navegación, llenar formularios, tomar screenshots.

**Requisitos:** Chrome debe estar corriendo con remote debugging (gestionado por daemon automático)

**Herramientas disponibles:**
- `mcp__chrome-devtools__navigate_page` - Navegar a URLs
- `mcp__chrome-devtools__click` - Hacer click en elementos
- `mcp__chrome-devtools__fill` - Llenar campos de texto
- `mcp__chrome-devtools__take_screenshot` - Capturar pantalla
- `mcp__chrome-devtools__take_snapshot` - Obtener árbol de accesibilidad

**Nota:** Usa un perfil de Chrome separado (`~/.chrome-debug-profile`), no el perfil principal.

## Browser Tools MCP

Captura datos del navegador: console logs, network requests, auditorías.

**Requisitos:** DevTools debe estar abierto con el panel "BrowserToolsMCP" visible

**Herramientas disponibles:**
- `mcp__browser-tools__getConsoleLogs` - Ver logs de consola
- `mcp__browser-tools__getConsoleErrors` - Ver errores
- `mcp__browser-tools__getNetworkLogs` - Ver requests de red
- `mcp__browser-tools__takeScreenshot` - Capturar pantalla
- `mcp__browser-tools__runAccessibilityAudit` - Auditoría de accesibilidad
- `mcp__browser-tools__runPerformanceAudit` - Auditoría de performance

## Gestión de servicios (macOS)

```bash
# Chrome Debug Daemon
launchctl start com.chrome-debug.daemon
launchctl stop com.chrome-debug.daemon
cat /tmp/chrome-debug-daemon.log

# Browser Tools Server
launchctl start com.browser-tools.server
launchctl stop com.browser-tools.server
cat /tmp/browser-tools-server.log
```

## xbar Plugin (Menu Bar Status)

**Ubicación:** `~/Library/Application Support/xbar/plugins/browser-mcp.5s.sh`

**Muestra:**
- 🌐 = Ambos servicios funcionando
- 🌐❗ = Algún servicio con problemas

**Ver también:** `~/.claude/CLAUDE.md` sección "Browser MCPs - Menu Bar Status" para código completo del plugin
