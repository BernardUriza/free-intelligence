# fenix — el experimento: ¿fi-glass es un framework, o era og118 con carpetas?

**Fecha:** 2026-07-27 · **Regla dura:** durante la construcción NO se toca
`apps/packages/fi-glass/`. Cada vez que dieron ganas de tocarlo, se anotó aquí.
Esa lista **es** el veredicto.

## Punto de partida (medido, no supuesto)

Antes de escribir una línea:

| App | Líneas propias | Cómo consume fi-glass |
|---|---|---|
| og118/web | 4,484 | los módulos reales: `agent`, `shell`, `voice`, `identity`, `conversation`, `persona-selector`, `messages` |
| activist-os/web | 979 | **sólo CSS** (`theme.css`, `glass-chat.css`) y la clase `fi-glass-panel` |
| **fenix/web** | **513** | los módulos reales |

Ojo con activist-os: declara `fi-glass: workspace:*` pero **no importa ni un
componente de React**. Usa fi-glass como hoja de estilos. Así que antes de fenix,
fi-glass tenía **un solo consumidor de verdad** en dos meses: og118.

## Veredicto

**El canario ES clonable.** 513 líneas de TypeScript, build verde al primer
intento (TypeScript incluido), y **fi-glass no se modificó ni una línea**
(`git diff --stat apps/packages/fi-glass/` vacío). Todo lo pesado lo puso el
framework: transcript, mensaje optimista, fold del asistente, AgentPanel en vivo,
persistencia IndexedDB, adjuntar imágenes y el drawer responsive.

**Pero el framework no es autosuficiente.** Trae una capa de conocimiento tribal
que no está documentada en ningún lado y que sólo se descubre leyendo
`Og118AgentChat.tsx` línea por línea. Cuesta ~1 hora de arqueología, y sin ella
el resultado es una app que compila y se ve **rota**.

## Hallazgos

### H1 — `mapEvent` se copió entero (~110 líneas)
`lib/useFenixAgent.ts` contiene una copia casi literal del `mapEvent` de
`og118/web/lib/useOg118Agent.ts`. No tiene **una sola línea** específica de
og118: es puro mapeo del contrato nativo de fi-runner al union
`AgentStreamEvent` de fi-core. Que el segundo consumer deba copiarlo prueba que
ese mapeo pertenece al framework.
**Arreglo:** subirlo a fi-glass (o a fi-core) como `mapFiRunnerEvent`.

### H2 — El composer viene ROTO por default
fi-glass **sí** trae los estilos correctos del composer
(`.glass-chat-composer`, `.glass-chat-composer-input`: transparente, color del
tema), pero su propio `AutoResizeTextarea` renderiza sólo `class="resize-none"`
y **no se los aplica**. Son opt-in vía props:

```tsx
composerBoxClassName="glass-chat-composer"
composerTextareaClassName="glass-chat-composer-input"
```

Sin esas dos líneas el textarea queda **blanco con texto blanco** — invisible.
Le pasó a este consumer y se detectó sólo mirando el render, no el build.
**Arreglo:** que el componente aplique sus propias clases por default.

### H3 — La clase `glass-chat` en `<body>` es un interruptor, no decoración
`glass-chat.css` define ~20 tokens de color (`--glass-chat-text`,
`--glass-chat-surface`, `--glass-chat-bg-from`…) bajo `:root` y `.glass-chat`.
Sin `<body className="glass-chat">` el tema no se activa.
**Arreglo:** documentarlo, o activarlo desde el propio `AgentWorkspaceShell`.

### H4 — fi-glass NO trae paleta de color
Sus tokens propios (`tokens.css`) son sólo 5, todos de **material**:
`--glass-blur`, `--glass-blur-compact`, `--glass-opacity`, `--glass-saturation`,
`--glass-border`. La paleta vive en `glass-chat.css`. Nombres tipo `--fi-bg` /
`--fi-surface` / `--fi-text` **no existen**: inventarlos (como se hizo en el
primer intento de este consumer) deja la app en blanco sobre negro.

### H5 — Fuga del consumer dentro del framework: `--og-accent`
fi-glass referencia una variable con el prefijo de og118 en tres lugares:

```
src/messages/MessageModelBadge.tsx:46    var(--fi-accent, var(--og-accent, #34d399))
src/messages/MessageAuthorHeader.tsx:72  var(--fi-author-agent-bg, var(--og-accent, #34d399))
src/agent/AgentWorkspaceShell.tsx:126    outline: 2px solid var(--og-accent, #34d399)
```

No rompe nada (hay fallback en cascada), pero es el olor de un framework que
creció pegado a un solo consumidor. La vía limpia para otro consumer es definir
`--fi-accent`, que gana antes de llegar a `--og-accent`.
**Arreglo:** quitar `--og-accent` de fi-glass; que og118 lo mapee a `--fi-accent`.

### H6 — Tailwind: cada consumer repite el escaneo del dist
fi-glass hornea utilidades Tailwind en su `dist` y Tailwind no escanea
`node_modules`, así que **todo** consumer debe repetir en su `tailwind.config.js`:

```js
'../../packages/fi-glass/dist/**/*.{js,mjs}',
```

Ya estaba documentado como "VALIDATION_REPORT finding #3" en og118 — y sigue
siendo trabajo del consumer.

### H7 — El scaffolding canónico no existe
La skill `/new-consumer` dice ejecutar `scripts/new-consumer.sh`. **Ese script no
está en el repo.** Y `pnpm-workspace.yaml` lista las rutas una por una, así que
un consumer nuevo requiere editarlo a mano.

## Lo que funcionó sin tocar nada

`useAgentConversation` · `useConversationLibrary` ·
`useIndexedDBConversationLibrary` · `AgentWorkspaceShell` (con drawer
responsive) · `AgentConversationSurface` · `imageAttachments` · el fold del
turno · la persistencia. Eso es la mayor parte del valor, y salió gratis.

## Pendiente (Rule 0 — nada de esto está probado en runtime)

El shell renderiza y el build es verde, pero **el chat no se ha ejercido contra
el backend**: falta levantar `apps/og118/server`, poner el token y cotizar una
lista real de las 35 sesiones que ya existen, para comparar el resultado contra
el momtest de claude.ai. Hasta entonces esto es un mockup que compila, no una
app que sirve.

## Alcance (ToS)

fenix corre contra el backend de og118, que autentica el modelo con el
`CLAUDE_CODE_OAUTH_TOKEN` personal de Bernard (suscripción Max). Servir a
terceros con esa credencial rompe el ToS de Anthropic. **Esta app es de uso
personal (Bernard + Claude, fase de dogfood).** El día que el equipo de la
papelería la use, necesita su propia cuenta o una API key del negocio.
Ver memoria `[[og118-oauth-personal-use]]`.

---

# Backend (27-jul, mismo día)

**No se escribió un backend nuevo.** fenix corre sobre `apps/og118/server` — el
mismo runtime, el mismo `/chat/stream`, el mismo RAG — en otro puerto y con otra
persona. Duplicar 4,438 líneas habría sido reinventar lo canónico (Art. 6).

Cambio total al backend existente: **una línea**, retrocompatible.

```python
PERSONA_PATH = Path(os.environ.get("FI_PERSONA_PATH") or (… / "prompts" / "persona.md"))
```

Sin la variable, og118 se comporta exactamente igual que antes. Con ella, el
mismo binario sirve a un segundo consumer con su propia voz: la tesis
"1 build → N consumers" ejercida de verdad.

## Cómo se levanta

```bash
cd apps/og118/server
export CLAUDE_CODE_OAUTH_TOKEN=$(grep -oE 'sk-ant-[A-Za-z0-9_-]+' ~/.secrets/og118-claude-oauth.txt | head -1)
export FI_PERSONA_PATH=<repo>/apps/fenix/server/prompts/persona.md
export OG118_AUTH_MODE=bearer
export OG118_PROJECT_REGISTRY_PATH=$HOME/.fenix-data/projects.json
export OG118_CONVERSATIONS_PATH=$HOME/.fenix-data/conversations
export FI_RAG_STORE_PATH=$HOME/.fenix-data/fi_rag_store.h5
export OG118_ALLOWED_ORIGINS=http://localhost:3100,http://127.0.0.1:3100
./.venv/bin/uvicorn app:app --port 8119
```

## Hallazgos nuevos (backend)

### H8 — Rutas de contenedor como default local
`OG118_PROJECT_REGISTRY_PATH` y `FI_RAG_STORE_PATH` apuntan por default a
`/opt/fi/…`, que en una Mac da `PermissionError` y tumba el primer request con
500. El README no lo menciona.

### H9 — El origen CORS del consumer viene hardcodeado
`_DEFAULT_ORIGINS = "http://localhost:3000,…"` — el puerto de og118. Un segundo
consumer en otro puerto recibe **400 en el preflight** y el navegador reporta
sólo `Failed to fetch`, sin pista de CORS. Se arregla con
`OG118_ALLOWED_ORIGINS`, pero hay que saber que existe.

## E2E — verde, con un defecto real

Verificado en la app (no por curl): mensaje enviado desde
`http://localhost:3100`, el glass-box renderizó los 5 pasos en vivo con las
llamadas a `search_documents`, y la respuesta llegó firmada como **Fénix**.

Lo que salió bien:
- Abrió con la cita literal del candado anti-invención.
- **Forrado de lustre $13**, correcto, con la traza del renglón.
- No inventó lo que no encontró: lo mandó a «preguntar a la dirección».

**El defecto:** dijo que **no encontró el precio de los gises blancos** — y sí
está en la lista maestra (`Gises blancos comprimidos Baco (caja): $11`, POS
18/jul). Por `curl`, con la misma pregunta, SÍ lo encontró. Dos causas
probables, ninguna verificada todavía:

1. **Recall del RAG.** El documento de 22,070 chars se partió en **16 chunks**
   (~1.4k chars c/u). Una lista de 117 renglones de precio en chunks tan gruesos
   depende de que la búsqueda semántica acierte el chunk exacto.
2. **El modelo.** El turno corrió en **claude-sonnet-4-5** (lo dice el chip de
   provenance). Es el mismo modelo que el 14-jul ignoró las Instructions y se fue
   a comparar Office Depot con Amazon.

**RESUELTO el mismo día, y la hipótesis del modelo era FALSA.** Se repitió la
pregunta aislada — *"¿Cuánto cuestan los gises blancos comprimidos?"* — con el
MISMO modelo (`claude-sonnet-4-5`) y el MISMO corpus, y respondió:

> Gises blancos comprimidos Baco (caja): **$11** (precio de lista)
> → renglón de `lista-de-precios-y-reglas-de-venta.md`: "Gises blancos
> comprimidos Baco (caja): $11 (POS 18/jul, ticket Lidia Orozco)"

Correcto, con la traza al renglón exacto. Así que no era Sonnet: **era el recall
del RAG en preguntas de VARIOS artículos.** La primera pregunta pedía dos cosas
("forrado de lustre **y** gises blancos"); la búsqueda semántica trajo el chunk
del forrado y no el de los gises, y el modelo — correctamente — no inventó el que
no vio.

**Por qué esto importa más de lo que parece:** una cotización real ES una
pregunta de muchos artículos a la vez (la de estela quiroz tenía 19). Si el
recall se degrada con 2, el riesgo con 19 es que renglones válidos caigan en
"falta precio — preguntar a la dirección" y el presupuesto salga incompleto.
No es un fallo de seguridad (nunca inventa), pero sí de completitud.

**Pendiente #1 (reformulado):** medir el recall con una lista real de 15-20
artículos y, si se degrada, subir el `top_k` de `search_documents` o partir la
lista maestra en chunks por sección en vez de 16 bloques de ~1.4k chars.
