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

### H10 — `TITLE_MAX = 60` decapita datos en silencio
`free-intelligence-core/src/conversation/helpers.ts` trunca todo título a 60
caracteres. No avisa, no lanza, no marca: guarda lo que cabe.

Fénix guarda el expediente del cliente EN el título (la convención que el equipo
ya usaba: `fecha — alumno (escuela) — WhatsApp`), así que el corte se comía el
teléfono — exactamente el dato que el formulario existe para capturar:

```
enviado:  28 jul — Sofía Ramírez (Sec. Gómez de Mendiola 2°) — 33 3448 8256
guardado: 28 jul — Sofía Ramírez (Sec. Gómez de Mendiola 2°) — 33 3448
```

El formulario decía "guardado" y el número quedaba mutilado. Sólo se detectó
leyendo el registro del servidor después de guardar, no en la UI.

**Solución del lado del consumer** (fi-glass/core sin tocar): el presupuesto de
60 caracteres se gasta por prioridad — fecha, alumno y teléfono son intocables;
la ESCUELA se abrevia con elipsis hasta que el título quepa.
**Arreglo de raíz sugerido:** que el truncado del framework sea visible (avisar,
o exponer `TITLE_MAX`) en vez de recortar callado.

---

# Consolidación en fi-glass (27-jul)

El experimento corrió con la regla "no tocar fi-glass" para que el veredicto
fuera limpio. Cumplida y con veredicto emitido, lo que resultó ser del framework
sube al framework. Esto es lo que se consolidó:

## H2 — el composer ya no viene roto por default ✅
`AutoResizeTextarea` ahora aplica `glass-chat-composer-input` él mismo. La clase
va PRIMERO y el `className` del consumer se concatena después, así que quien
quiera otra cosa sigue ganando; y si el consumer no activa el tema
(`.glass-chat` en `<body>`), la regla es inerte.

**La prueba de que la consolidación sirvió:** fenix BORRÓ su
`composerTextareaClassName` y el composer sigue correcto — verificado en el
navegador, `class="glass-chat-composer-input resize-none"`, fondo transparente,
texto blanco. El consumer ya no necesita saber ese detalle.

## H5 — fi-glass ya no conoce a og118 ✅
Las tres referencias a `--og-accent` pasaron a `--fi-accent`. og118 mapea el
suyo (`--fi-accent: var(--og-accent)`) en su propio `globals.css`, así que el
acento sigue siendo el mismo verde pero la dependencia ahora va del consumer al
framework y no al revés. `grep -rn "og-accent" src/` en fi-glass: **cero**.
og118 recompila verde.

## Lo que NO se subió, y por qué
- **H1 (`mapEvent`)** — mover el mapeo fi-runner→core toca el contrato entre dos
  paquetes publicados; merece su propio PR con tests, no un arrastre.
- **H10 (`TITLE_MAX` trunca en silencio)** — el arreglo correcto es que el
  framework avise en vez de recortar callado, y eso cambia una firma pública.

Ambos quedan documentados arriba con su arreglo propuesto.

---

# H11 — el entregable no existía (27-jul)

Bernard preguntó "¿y las cotizaciones de Excel?" y destapó el hueco más grande
del proyecto.

**El modelo NO puede generar el archivo.** `ToolPolicy.companion()` le bloquea
`Bash`, `Write` y `Edit` (og118 #277 — un companion no debe tocar el filesystem
del host, y debe seguir siendo así). Verificado en runtime, no deducido: ante
"genera el Excel" el modelo intenta `Bash`, falla, se disculpa
("Permíteme intentar directamente…") y **entrega una tabla markdown en el chat**.

Ese es el peor modo de fallar: parece útil. Lo que se manda por WhatsApp a la
mamá del alumno es un `.xlsx`, no un mensaje — el chat es el medio, el Excel es
el producto. Toda la app estaba construida alrededor de algo que no producía su
entregable.

## La solución: el modelo pone los DATOS, el servidor pone el FORMATO

`apps/fenix/server/presupuesto.py` genera el .xlsx con openpyxl a partir de
datos estructurados, y `POST /expedientes/excel` lo sirve. Dos ganancias de un
movimiento:

1. **Seguridad**: no hay que abrirle ejecución de código arbitrario a un
   companion para producir una hoja de cálculo.
2. **El formato queda invariante por construcción.** Las Instructions repiten
   "PLANTILLA … NO alterar formato" precisamente porque un modelo que ejecuta el
   script puede improvisar el diseño. Si el script vive en el servidor, no hay
   nada que improvisar — y la regla "la rotulación no lleva descuento" se cumple
   sola en vez de depender de que el modelo la recuerde.

Verificado releyendo el archivo generado y comparando contra un cálculo
independiente: subtotal 496, ahorro 74.40, total 421.60. Cuadra.

## Dos defectos encontrados en el camino, ninguno visible en el build

- **`items: undefined` reventaba la app.** Los 33 expedientes migrados se
  escribieron antes de que el campo existiera, y `e.items.length` lanzaba
  `Cannot read properties of undefined`. Arreglado en los dos lados: el store
  completa la forma al LEER (un store que gana campos con el tiempo debe
  devolver siempre la forma completa) y el cliente no asume la forma de lo que
  llega de una API.
- **El nombre del archivo salía genérico.** CORS oculta `Content-Disposition`
  al JavaScript salvo que se exponga explícitamente, así que la descarga era
  "Presupuesto.xlsx" en vez de "Presupuesto-Emma-Hernandez-4B.xlsx". El archivo
  viaja por WhatsApp: su nombre tiene que decir de quién es sin abrirlo.

## Lo que falta para cerrar el círculo

Los renglones llegan al expediente por API, pero **el modelo todavía no los
escribe solo** al cerrar una cotización. Hoy hay que pasarlos; el paso que falta
es una herramienta MCP que le permita guardar el desglose en el expediente.
Mientras tanto el botón "Excel" sólo aparece en los expedientes que ya tienen
renglones — un botón que descarga una hoja vacía es peor que no tenerlo.

## H11 cerrado — el círculo completo (27-jul)

**El modelo ya guarda la cotización solo.** `apps/fenix/server/fenix_mcp.py`
expone `guardar_cotizacion` por MCP stdio, y `runner.py` gana un punto de
extensión genérico (`FI_EXTRA_MCP="nombre:/ruta/modulo.py"`) para que un
consumer registre su herramienta sin que og118 la conozca. Sin la variable,
og118 se comporta idéntico.

Por qué una herramienta acotada y no `Bash`: con Bash el modelo podría escribir
el archivo… y cualquier otro. Una herramienta le deja hacer EXACTAMENTE una
cosa. El Excel lo sigue generando el servidor.

**Verificado end-to-end**: se pidió "cotiza para Diego Sánchez…" y el modelo,
sin que nadie se lo recordara, buscó los precios en la lista maestra y llamó
`mcp__fenix-expedientes__guardar_cotizacion`. El expediente apareció con alumno,
escuela, grado, WhatsApp y 3 renglones a precio de lista.

**Discrepancia encontrada de paso**: el modelo escribió "$196.35" en su prosa y
guardó $251.60 en la herramienta. El cálculo correcto es 2×65 + 159 + 7 = 296,
−15% = **251.60**: el dato guardado está bien y la aritmética del texto no. Es
un argumento a favor del diseño — **el Excel se genera del dato estructurado, no
de la prosa**, así que el archivo sale correcto aunque el chat se equivoque.

## Visor del presupuesto

`POST /expedientes/excel/vista` genera el MISMO archivo que la descarga y lo
parsea con openpyxl (celdas, colores, combinaciones, formatos). El visor pinta
eso.

**Por qué parsear el archivo y no dibujar desde los datos de entrada**: si el
visor re-interpretara el input, podría mostrar algo distinto a lo que se
descarga. Una vista previa infiel es peor que ninguna, porque se confía en ella
para decidir si mandarla. Una sola fuente: el archivo.

## H12 — el composer no tenía paddings (y og118 hacía trampa)

`.glass-chat-composer` pintaba la caja —fondo, borde, radio, sombra, blur— y
**no daba padding a nada**: el placeholder quedaba pegado al borde izquierdo y
el botón de enviar contra la esquina. og118 lo tapaba con clases PROPIAS
(`.og-composer-area`, `.og-composer-controls`) pasadas por **cinco** props de
className distintas. O sea: el default del framework era feo y cada consumer
tenía que descubrirlo y arreglarlo por su cuenta. Mismo patrón que H2.

**Arreglo en el framework.** Las zonas del composer se marcan con
`data-fi-composer-slot`, así que el tema puede vestirlas sin inventar clases:
`area` (que era la ÚNICA zona sin marcar — se le añadió el atributo), `footer` y
`header`. Un className del consumer sigue ganando por especificidad, así que
og118 no cambia.

Medido en el navegador: el texto pasó de pegado al borde a **15px** de respiro,
con fenix sin pasar una sola clase de padding.

## RBAC — dos superficies sobre la misma IA

La papelería tiene dos públicos en el mismo local: el mostrador (cotiza, ve
expedientes) y el minicibercafé de afuera (niños haciendo tarea en PCs
compartidas). Sin separación, cualquiera en el cibercafé veía la lista completa
de expedientes: nombres de alumnos, escuelas y WhatsApps de las mamás de otras
familias. Datos de menores en una máquina pública.

### El token del mostrador, no un proveedor de identidad

La primera versión usó una lista de correos (`FENIX_ADMIN_EMAILS`) y anunciaba
que "la separación de verdad llega con Auth0". Se intentó y se descartó: un IdP
pide tenant, callbacks por entorno, refresh tokens y consentimiento para
distinguir a tres personas que trabajan detrás del **mismo** mostrador — y la
separación real de este local no es entre personas, es entre **las PC de adentro
y las de afuera**.

Lo que quedó modela exactamente eso:

- **`FENIX_ADMIN_TOKEN` autoriza.** Es el secreto de la papelería, se pega una
  vez en cada PC del mostrador y vive en su `localStorage`. Las máquinas del
  ciber simplemente no lo tienen. Se revoca cambiando una variable. Comparación
  en tiempo constante — un `==` filtra el token carácter a carácter ante quien
  pueda medir la respuesta.
- **`X-Fenix-Email` identifica.** Dice QUIÉN trabajó una cotización; no abre
  ninguna puerta. Un correo fuera de `FENIX_ADMIN_EMAILS` se marca en la píldora
  sin bloquear, porque casi siempre es un dedazo que deja la cotización difícil
  de rastrear.

Sin token configurado, todo el mundo es mostrador: es el default de desarrollo,
y tanto el arranque como `/expedientes/rol` lo reportan para que nadie lo
despliegue así sin verlo.

### H13 — la lista de cotizaciones estaba abierta a cualquiera

El hallazgo más grave del experimento, y sólo apareció al ir a corregir un
comentario. `GET /conversations` respondía **200 sin ninguna credencial**: los
títulos llevan nombre del alumno, escuela y el WhatsApp de la mamá. Cualquiera
que alcanzara el servidor —empezando por las PC del ciber— podía leer la lista
completa. Ocultarla en la barra era cosmética, y el propio comentario del código
lo admitía mientras prometía una puerta que nunca llegó.

La causa es estructural y vale para cualquier consumer que herede la app de
og118: **og118 sirve `/conversations` y `/projects` abiertas porque es una app
de una sola cuenta.** Un consumer con dos públicos hereda ese supuesto sin
enterarse.

Se cierran inyectando la dependencia en las rutas ya registradas, **no con un
middleware**: el middleware queda por fuera del CORS de og118 (Starlette pone
más afuera lo último añadido) y el navegador recibiría un error de red opaco en
lugar del 404 que el cliente distingue para pintar la vista pública. Verificado:
el 404 llega con `access-control-allow-origin`.

Como la puerta se pone mutando rutas ajenas, un rename en og118 la reabriría en
silencio — el arranque **falla** si no cierra ninguna, y un test lo afirma
(`tests/test_puerta_mostrador.py`, 7 verdes).

Cerrar la puerta destapó tres defectos más, ninguno visible en el build:

1. La librería remota mandaba el bearer pero **no** el token del mostrador, así
   que se ganaba su propio 404 y la barra quedaba vacía.
2. La píldora leía `localStorage` durante el render → el servidor pintaba vacío,
   el cliente pintaba iniciales, y React tiraba el árbol por la discrepancia.
3. El cibercafé recibía la app del mostrador entera ("Nueva cotización", "manda
   la foto de la lista") cuando son niños con veinte minutos de tarea.

### H14 — el framework no sabía NO guardar

fi-glass tenía dos implementaciones de `ConversationLibrary` y **ambas
persisten**: IndexedDB (navegador) y Remote (servidor). En una terminal
compartida eso no es una funcionalidad ausente sino un riesgo: IndexedDB es del
navegador, no de la persona, así que cada niño heredaría la conversación del
anterior.

Es el caso canónico de `framework-first-canary` con un consumer que **no** es el
canario: la capacidad es reusable (cualquier shell con modo kiosco la quiere),
así que subió a fi-glass como `EphemeralConversationLibrary` y fenix es su
primer consumer. 61 líneas contra el mismo contrato, 6 tests.

**Verificado en runtime**, no en el build: sin token, la PC pública contestó
`7 x 8 = 56` y explicó la fotosíntesis para 5º de primaria, sin tocar
`/conversations`; con token, los 33 chats y las dos pestañas vuelven.
