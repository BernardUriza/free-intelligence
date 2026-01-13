2025-10-25 12:45 - INICIO - Importación de tarjetas desde CSV

## 🎯 Trello CLI v2.2.0 - Intelligent Card Movement Analysis (REQUIRED)

**All card movements must use Trello CLI v2.2.0 with Claude AI analysis:**

```bash
trello quick-start <card_id>    # Start work + automatic analysis
trello quick-test <card_id>     # Move to testing + analysis
trello quick-done <card_id>     # Complete + analysis
```

2025-10-25 12:46 - Tarjeta P0 creada: [P0][Infra] Crear tablero + listas + labels
2025-10-25 12:46 - Tarjeta P0 creada: [P0][Backend] Extraer ConversationCapture (symfarmia/dev)
2025-10-25 12:46 - Tarjeta P0 creada: [P0][UI+Backend] Triage Intake (FI endpoints + whisper npm)
2025-10-25 12:46 - Tarjeta P0 creada: [P0][Infra] Storage local sin PHI (buffers/manifest)
2025-10-25 12:46 - Tarjeta P0 creada: [P0][Security] RBAC admin omnipotente
2025-10-25 12:46 - Tarjeta P0 creada: [P0][Demo] Script de demo (3 casos V/A/R)
2025-10-25 12:47 - Tarjeta P0 creada: [P0][Build] Build reproducible (Docker/Node 20) + tags v0.1.0
2025-10-25 12:47 - Tarjeta P0 creada: [P0][Infra] Repo/Entorno listo (main, aurity/, .env.local)
2025-10-25 12:47 - Tarjeta P0 creada: [P0][QA] Criterios de aceptación empaquetados
2025-10-25 12:47 - Tarjeta P1 creada: [P1][Export] Export evidencia demo (PDF/MD)
2025-10-25 12:47 - Tarjeta P1 creada: [Optional][Infra] NAS local
2025-10-25 12:48 - Tarjeta Blocked creada: [Blocked][Infra] Acceso repo symfarmia
2025-10-25 12:48 - Tarjeta Blocked creada: [Blocked][Infra] Trello API key/token
2025-10-25 12:48 - Tarjeta Blocked creada: [Blocked][Infra] Node 20 + Docker
2025-10-25 12:48 - COMPLETADO - 9 P0, 2 P1, 3 Blocked
2025-10-25 12:50 - Tarjeta Philosophy creada: AU-PHIL-DOC-001 - Filosofía de Soberanía de Datos
2025-10-25 12:51 - Tarjeta Architecture creada: AU-ARCH-DOC-001 - Arquitectura Free Intelligence Core
2025-10-25 12:51 - Tarjeta Vision creada: AU-VISION-DOC-001 - Roadmap FI-Health 4 Fases
2025-10-25 12:52 - Tarjeta Technical creada: AU-TECH-DOC-001 - Stack Técnico y Hardware NAS
2025-10-25 12:52 - COMPLETADO - Philosophy & Architecture section poblada con 4 tarjetas fundamentales
2025-10-25 12:55 - Tarjeta Commercial creada: AU-VALUE-DOC-001 - Propuesta de Valor Comercial
2025-10-25 12:55 - ACTUALIZADO - Philosophy & Architecture con 5 tarjetas (añadida value proposition)
2025-10-25 14:00 - ACTUALIZACIÓN - Trello CLI migrado a v2.0
   • Ubicación: ~/Documents/trello-cli-python/
   • Comando global: 'trello' (disponible desde cualquier directorio)
   • Arquitectura modular: commands/, utils/, tests/
   • Backward compatibility: alias 'trello-cli.py' funciona
   • Documentación: ~/Documents/trello-cli-python/README.md
   • Uso: trello boards | trello lists <board_id> | trello cards <list_id>
2025-12-20 09:00 - ACTUALIZACIÓN - Migración a estructura modular backend/src
   • Nuevo path: backend/src/fi_*
   • FastAPI app principal en backend/app/main.py
   • Rutas públicas en backend/api/public/workflows/
   • Rutas internas en backend/api/internal/
   • Almacenamiento HDF5 y workers en backend/src/fi_storage/ y backend/workers/
   • Documentado en .github/copilot-instructions.md

---

## Browser MCPs (Automatización de Navegador)

### Chrome DevTools MCP (Interacción con el navegador)
Permite interactuar con Chrome: clicks, navegación, llenar formularios, tomar screenshots.

**Requisitos**: Chrome debe estar corriendo con remote debugging (gestionado por daemon automático)

**Herramientas disponibles**:
- `mcp__chrome-devtools__navigate_page` - Navegar a URLs
- `mcp__chrome-devtools__click` - Hacer click en elementos
- `mcp__chrome-devtools__fill` - Llenar campos de texto
- `mcp__chrome-devtools__take_screenshot` - Capturar pantalla
- `mcp__chrome-devtools__take_snapshot` - Obtener árbol de accesibilidad

**Nota**: Usa un perfil de Chrome separado (`~/.chrome-debug-profile`), no el perfil principal.

### Browser Tools MCP (Monitoreo)
Captura datos del navegador: console logs, network requests, auditorías.

**Requisitos**: DevTools debe estar abierto con el panel "BrowserToolsMCP" visible

**Herramientas disponibles**:
- `mcp__browser-tools__getConsoleLogs` - Ver logs de consola
- `mcp__browser-tools__getConsoleErrors` - Ver errores
- `mcp__browser-tools__getNetworkLogs` - Ver requests de red
- `mcp__browser-tools__takeScreenshot` - Capturar pantalla
- `mcp__browser-tools__runAccessibilityAudit` - Auditoría de accesibilidad
- `mcp__browser-tools__runPerformanceAudit` - Auditoría de performance

### Gestión de servicios
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

