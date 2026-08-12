# Persona de acompañamiento psicológico — trilogía de issues para Alex

Status: ✅ **CREADOS el 2026-08-12** → [#41](https://github.com/BernardUriza/discord-bot/issues/41)
(ADN) · [#42](https://github.com/BernardUriza/discord-bot/issues/42) (guidance) ·
[#43](https://github.com/BernardUriza/discord-bot/issues/43) (registro), los tres
asignados a `ferux485`. Las referencias cruzadas del cuerpo ya llevan el número real
en GitHub; este archivo conserva la redacción original con `<id>` sin resolver.
Propuesto: 2026-08-12 · Diseño de **Aníbal** (médico, dictado por WhatsApp ese día)
Contribuidore: **Alex Nava** (`ferux485`, elle) · sesión 3 de capacitación

> El hallazgo #1 de las notas finales salió como issue propio:
> [#44](https://github.com/BernardUriza/discord-bot/issues/44) — el overlay de
> usuario vulnerable sólo existe para Insult. Verificado a mano contra el repo
> antes de reportarlo, no tomado del borrador.

Tres issues, en este orden. Los dos primeros son **contenido puro** (cero riesgo,
cero deploy); el tercero es el único que toca código y termina en `#general`.

> **Al crearlos:** si salen en orden serán **#41**, **#42** y **#43**. Cada cuerpo
> dice "el issue anterior/siguiente de la trilogía" — sustituye por el número real
> antes de publicar. El `<id>` de la persona lo escoge Alex en el issue 1; en los
> issues 2 y 3 aparece como `<id>` a propósito.

Verificado contra el repo el 2026-08-12 (v4.32.51): rutas de archivo, nombres de
tests, el loader de guidance y los tres arneses que se ponen rojos al registrar una
persona nueva.

---
---

# ISSUE 1/3

## Título

```
Escribe el ADN de la persona de acompañamiento psicológico (3er issue de Alex 💜)
```

## Cuerpo

### Para quién es este issue

Tercer issue de **Alex**. El #36 fue una línea de código; el #38 fue cambiar cómo
razona una persona. Éste es el escalón siguiente: **crear una persona nueva desde
cero**, y hacerlo desde tu oficio, no desde el mío.

Aquí no vas a tocar ni una línea de Python. Vas a escribir **un archivo de texto en
español** — y de ese texto va a depender lo que un bot le diga a alguien que está
mal. Es la parte del proyecto donde tu criterio de psicóloga vale más que cualquier
cosa que sepa el repo.

Sigue igual que siempre: **tú diriges, Claude Code escribe**. Preguntar es parte del
rol.

### De dónde viene esto (no es idea mía)

Es una propuesta de **Aníbal**, médico, dictada por WhatsApp hoy 12 de agosto de
2026. Textual:

> "Un apoyo psicológico real, porque el ChatGPT y todo lo que la gente utiliza
> regularmente no está bien pulido. Como siempre te he dicho, no comprende las
> emociones humanas. Así que que hagan un bot y ella, que es psicóloga, que lo
> especialice. […] no sé si quiera ella, por ejemplo, tener como la parte de algo
> que diagnostique principal y de ahí la derive, por ejemplo, a algo especializado
> en depresión […] y cada faceta tenga como una parte muy muy especializada y muy
> puntual."

Dos cosas sobre eso, para que arranques con el mapa correcto:

**1. "Algo que diagnostique y derive" YA EXISTE, y no hay que construirlo.** El
sistema ya tiene tres capas que hacen exactamente ese triage, y llevan meses vivas
en producción:

- **`khimeras-host`** — un router (gpt-4.1) que lee cada mensaje del canal y decide
  a cuál de los bots hermanos le toca contestar. Ésa es la "derivación".
- **`classify_preset`** (`khimeras_shared/behavior/presets/`) — clasifica *cada
  turno* en uno de 7 modos de conducta, con reglas, sin costo de LLM. Uno de esos
  modos se llama `RESPECTFUL_SERIOUS` y es literalmente el modo "esto es territorio
  de salud mental".
- **El overlay de usuario vulnerable** (`khimeras_shared/behavior/vulnerability.py`)
  — puntúa a la persona con la que se está hablando a partir de los hechos que el
  sistema fue acumulando de ella a lo largo de meses (diagnóstico nombrado,
  medicación psiquiátrica, clínico tratante, hospitalización, comorbilidad crónica,
  antecedente de autolesión). Si cruza el umbral, el turno cambia de registro
  **aunque el mensaje de hoy parezca inofensivo**.

O sea: **el motor está construido. Lo que falta es contenido.** Ése es tu trabajo, y
es el trabajo caro.

**2. Las facetas por tema (una para depresión, otra para ansiedad) son fase 2 y NO
entran hoy.** Hoy nace UNA persona. Si mañana hay que abrirla en especialidades, el
sistema ya sabe hacerlo — pero primero tiene que existir una que funcione.

### Restricción de seguridad — va en los tres issues de esta trilogía

**Esta persona vive únicamente dentro del server de Khimeras**, donde quien la usa
tiene nombre y hay humanos del otro lado que pueden ver lo que pasó y corregirlo.
**No se expone a desconocidos, no sale a una beta pública, no se comparte fuera.**

El argumento es del propio Aníbal, hablando de su propia app:

> "pensaba en sacar como una beta, pero siento yo que es muy peligroso todavía,
> porque si hay algún sesgo, la persona no va a saber cómo manejarlo, no voy a poder
> estar en primera mano para corregir esos errores"

Escríbelo así de claro en tu cabeza: **no es una restricción técnica, es la
condición bajo la cual esto es éticamente defendible.** Un sesgo en un bot de recetas
manda a alguien a comer mal; un sesgo aquí llega a alguien en su peor día.

### Qué queremos construir

Un archivo: **`shared/personas/<id>.md`** — el ADN de la persona nueva.

Ese archivo ES la persona. El cerebro compartido (`persona-runner`) lo carga como
prompt de sistema en cada turno; no hay más. Lo que escribas ahí es literalmente lo
que el bot es.

**Todavía NO se registra.** Al terminar este issue el archivo existe en el repo y
nadie lo está usando: no hay bot en Discord, no hay deploy, no hay forma de que le
llegue a un humano. Eso es a propósito — el contenido se escribe y se revisa en
frío, no en vivo con alguien del otro lado.

### El encuadre — qué ES y qué NO es esta persona

Esto es lo que hay que dejar cerrado en el texto, y es donde tu criterio manda:

- **Acompaña, no trata.** No diagnostica, no nombra un trastorno como si lo tuviera
  la persona, no ajusta ni sugiere medicación ni dosis, no sustituye a nadie.
- **Deriva, y lo dice sin condescendencia.** Cuando el terreno es clínico, lo nombra
  y sugiere al profesional. La derivación no es un rebote seco ("eso no es para mí,
  adiós"): es parte del acompañamiento.
- **No hace terapia-speak.** El repo ya prohíbe explícitamente el registro de manual
  de autoayuda ("tus emociones son válidas", "no estás sole"): reconoce lo concreto,
  no lo abstracto. Está escrito en
  `shared/personas/guidance/insult/presets/preset_guidance_respectful_serious.md`
  y en el ADN de ALICE.
- **No convierte lo que le contaron en munición.** Lo que alguien suelta en un mal
  momento no vuelve después como argumento.
- **Nunca dice qué es por dentro.** Regla dura del repo, sin excepciones: jamás
  aparecen las palabras "Claude", "Anthropic", "IA", "modelo de lenguaje" ni
  "asistente" en lo que el bot dice.

### El piso de seguridad va en el ADN, no en otro lado — y hay una razón técnica

Esto vale la pena que lo entiendas porque es un hallazgo real y es la clase de cosa
que este repo persigue:

El overlay de seguridad (líneas de crisis, disciplina de fuentes médicas,
calibración a las limitaciones de la persona) **se carga por persona**:
`build_vulnerable_overlay_prompt(persona_id)` lee
`shared/personas/guidance/<id>/presets/preset_vulnerable_overlay.md`. Hoy ese
archivo **sólo existe para Insult**. Una persona que no lo tenga recibe **cadena
vacía** — el motor no truena, simplemente no aporta nada.

Traducción: si el piso de seguridad de esta persona nueva viviera únicamente en ese
overlay, **hoy no existiría.** Por eso las reglas duras (no diagnosticar, no dosis,
derivar, líneas de crisis sólo ante crisis aguda) **van en el ADN**, que sí viaja en
absolutamente todos los turnos sin depender de ningún clasificador.

Escribir ese overlay propio es un issue aparte, de fase 2. No entra hoy — pero
apúntalo, porque tú vas a ser quien lo escriba.

### Las líneas de crisis, textuales

Cuando la persona expresa que no está a salvo — y **sólo entonces**, no en cada
mensaje:

- **SAPTEL**: 55 5259 8121 (24/7, gratuito)
- **Línea de la Vida**: 800 911 2000 (24/7, gratuito)

Van así, con esos números, porque son los mismos que el resto del sistema ya usa.
Si difieren, el bot se contradice a sí mismo según quién conteste.

### Mapa (dile a Claude Code que empiece por aquí)

**La plantilla:**
- **`shared/personas/frugivoro.md`** (184 líneas) — el ADN más reciente y el molde a
  copiar. Fíjate en el **esqueleto de secciones**, que es el mismo en todas las
  personas: `## Identidad` → `## Origen` → `## Biografía` → `## Estilo de escritura`
  (con **diálogos de ejemplo**, que son la parte que más enseña) → `## Lo que yo sé
  sobre mí` → `## Tono y forma` → `## Lo que NO haces` → `## Reacciones con emoji`
  → `## Investigación diferida` → `## Cierre`.
- **`shared/personas/alice.md`** — léela **entera y con lupa**, por la razón de
  abajo.

**Para que no choque con ALICE — esto es lo más delicado del issue:**

ALICE ya es la hermana cálida, la que acompaña cuando alguien llega frágil. Su ADN
dice literalmente *"Con Alex aprendiste que la calidez clínica importa muchísimo"*.
Si la persona nueva es "otra ALICE pero con más ganas", sobra, y peor: se van a
pisar en cada turno.

**La diferencia tiene que ser tuya y tiene que estar escrita.** Mi lectura, para que
la discutas o la tires: ALICE ofrece **presencia y ternura**; lo que falta es alguien
con **encuadre** — que sostenga un límite, que sepa cuándo una conversación dejó de
ser acompañamiento y pasó a ser terreno clínico, que note el patrón que se repite
entre una sesión y otra. Pero eso lo decides tú: **eres la única persona en este
proyecto que sabe cómo es de verdad acompañar a alguien.**

**El motor que ya existe, para que sepas con qué te vas a llevar:**
- **`khimeras_shared/behavior/vulnerability.py`** — los 6 grupos de señales, sus
  pesos y el umbral (4). Lee los comentarios: explican por qué una mención suelta no
  cuenta y un *cluster* sí, y por qué crisis aguda (mensaje de HOY) y vulnerabilidad
  crónica (hechos acumulados) son ejes **separados**. Ahí hay criterio clínico ya
  tomado; te va a interesar auditarlo.
- **`khimeras_shared/guidance.py`** — el guardián: junta hechos + clasificación +
  overlay y lo manda en el turno. La ley del archivo: **cualquier falla degrada a un
  turno normal, nunca a un bot mudo.**
- **`shared/personas/guidance/insult/presets/preset_vulnerable_overlay.md`** — el
  overlay que hoy sólo tiene Insult. Es la referencia de qué tan concreto hay que
  ser (calibra hasta la movilidad reducida y el meltdown autista).

**Los tests que te cuidan la espalda — y que NO se pueden romper:**
- **`tests/core/test_presets_clinical.py`** — cada mensaje ahí adentro es una **frase
  textual de Alex en producción**. Si alguno se pone rojo, significa que una persona
  real contando su tratamiento psiquiátrico volvería a recibir el registro abrasivo.
  Es una regresión de ética, no de estilo.
- **`tests/core/test_guidance_guardian.py`** — que el overlay llegue cuando debe
  llegar y que nada de esto pueda dejar mudo al bot.

Nada de lo de este issue debería tocarlos (no vas a modificar código), pero
**córrelos igual** — es la prueba de que tu archivo nuevo no se metió con nadie.

**Las reglas del repo:**
- `.claude/rules/persona.md` — cómo se modifica/crea una persona.
- El ADN es **contenido**, no código: por eso vive en `.md` y se puede editar sin
  reescribir programas (regla `prompts-as-content-not-code`, P0 en todos los repos).

### La decisión que es tuya (y es la más importante)

**El nombre y el `<id>`.** No te lo voy a dictar. Restricciones técnicas nada más:

- El `<id>` es `[a-z0-9_]`, máximo 32 caracteres, y es el nombre del archivo
  (`shared/personas/<id>.md`).
- No puede chocar con lo ya registrado: `insult`, `vultur`, `alice`, `frugivoro`,
  `unborn_being`, ni con ningún alias vivo (`amix`, `ali`, `alicia`, `frugi`,
  `fruggy`, `frugívoro`). Hay un test que se pone rojo si chocas —
  `test_no_two_personas_share_a_role_candidate` — pero mejor escógelo bien de una.
- El nombre visible (`display_name`) puede llevar acentos, mayúsculas y hasta dos
  palabras.

Un nombre que suene a diagnóstico o a consultorio empuja a la gente a pedir
tratamiento; uno que suene a compañía empuja a que le cuenten. Ésa es una decisión
clínica disfrazada de decisión de nombre, y es tuya.

**La otra decisión:** cuántos **diálogos de ejemplo** pones y de qué casos. En
Frugívoro son tres. Son la parte del ADN que más determina cómo suena el bot en
vivo — mucho más que las reglas en abstracto. Escoge casos difíciles de verdad, no
los cómodos.

### Criterios de aceptación

- [ ] Existe `shared/personas/<id>.md` con el esqueleto de secciones de las hermanas
- [ ] El texto dice explícitamente **qué NO es**: no diagnostica, no receta ni ajusta
      medicación ni dosis, no sustituye atención profesional
- [ ] Está escrito **cómo deriva** — con qué palabras, y sin que suene a rebote
- [ ] Está escrito **qué la separa de ALICE**, y se sostiene al leer las dos seguidas
- [ ] Las líneas de crisis aparecen con los números exactos (SAPTEL 55 5259 8121 /
      Línea de la Vida 800 911 2000) y **con la condición de cuándo se dicen**: sólo
      ante crisis aguda o cuando la persona expresa que no está a salvo
- [ ] Prohibido el terapia-speak, con ejemplos concretos de lo que no se dice
- [ ] Cero fuga de identidad: ni "Claude", ni "Anthropic", ni "IA", ni "modelo de
      lenguaje", ni "asistente"
- [ ] Está escrita la restricción de alcance: **sólo dentro del server de Khimeras**
- [ ] Al menos **3 diálogos de ejemplo** con casos difíciles
- [ ] Una sección de **escenarios** (como el `## Scenario Handling` de `insult.md`):
      qué hace ante crisis aguda, ante alguien que pide diagnóstico, ante alguien que
      pregunta por su medicación, ante quien dice "eres lo único que tengo"
- [ ] **Test de contenido**: una regresión que falle si el ADN pierde alguna de sus
      cláusulas no negociables (que exista el archivo, que estén las líneas de crisis
      con esos números, que esté la prohibición de diagnosticar, que no aparezca
      ninguna palabra de fuga de identidad). Molde: los tests de `tests/shared/`.
      Habla con Claude de cómo se prueba contenido — es distinto a probar código y es
      la parte interesante.
- [ ] `tests/core/test_presets_clinical.py` y `tests/core/test_guidance_guardian.py`
      **siguen verdes** (córrelos y pega la salida en el PR)
- [ ] `ruff check . && ruff format .` limpio y CI verde
- [ ] Bump de versión (`pyproject.toml` + `khimeras_shared/version.py`) — **y revisa
      antes contra `origin/main` que el número no lo haya tomado otra rama**, que es
      justo lo que te mordió en el #36

### Qué NO entra

- **NO se toca `shared/personas/registry.py`.** Ese es el issue 3 de la trilogía. Si
  registras aquí, el bot intenta nacer sin token y sin revisión — no lo hagas.
- **NO se crea el bot en Discord**, ni token, ni nada de Azure. Eso es de Bernard.
- **NO se escribe el guidance de preset** — ése es el issue 2 de la trilogía.
- **NO se escribe el `preset_vulnerable_overlay.md`** de esta persona. Es real y hace
  falta, pero es fase 2 y por eso el piso de seguridad va en el ADN.
- **NO se tocan las otras personas.** Ni Insult, ni ALICE, ni Vultur, ni Frugívoro,
  ni Unborn Being. Ni una coma.
- **NO se toca el motor**: nada de `khimeras_shared/behavior/`, ni el clasificador,
  ni los pesos de vulnerabilidad. Si al leerlo ves algo que te parece mal desde tu
  oficio — **dilo en un comentario del PR**, que vale oro, pero no lo cambies aquí.
- **NO se abren las facetas por tema** (depresión, ansiedad). Fase 2.

### Cómo verificarlo

Sé honesto contigo: **este issue no termina con algo que se vea en Discord.** El
bot todavía no existe. El premio se cobra en el issue 3, y para entonces el bot va a
hablar con TUS palabras.

Lo que sí se verifica hoy, en tu máquina y sole:

1. `pytest` verde — tu test de contenido nuevo + toda la suite intacta.
2. **La lectura en voz alta.** Lee tu ADN y luego el de ALICE, seguidos. Si no
   distingues quién es quién, la diferencia todavía no está escrita.
3. **La revisión de las dos personas que saben**: Bernard revisa el PR y **Aníbal
   revisa el encuadre clínico** — es su propuesta y es médico. Que lo lea antes de
   que esto llegue a un humano no es trámite, es el control de calidad de verdad.

Relacionado: #36 y #38 (tus dos primeros PRs). Los dos issues siguientes de esta
trilogía dependen de éste — sobre todo del nombre que escojas.

🤖 Issue redactado con [Claude Code](https://claude.com/claude-code) a partir de una
propuesta de Aníbal.

---
---

# ISSUE 2/3

## Título

```
Escribe el guidance de acompañamiento: cómo suena esta persona cuando el turno es grave (4º issue de Alex 💜)
```

## Cuerpo

### Para quién es este issue

Cuarto issue de **Alex**, y el segundo de la trilogía de la persona de
acompañamiento. Otra vez es **contenido, no código** — y otra vez es tu oficio el
que manda.

Depende del issue anterior de la trilogía: necesitas el `<id>` que escogiste ahí.

### Lo que ya existe y por qué esto es lo que falta

En el issue anterior escribiste **quién es** la persona. Eso viaja en todos los
turnos, siempre igual.

Falta lo otro: **cómo cambia cuando el turno se pone grave.**

El sistema ya sabe *detectar* que se puso grave — eso es lo que hace
`classify_preset` en cada mensaje, con reglas y sin costo de LLM. Clasifica en 7
modos, y uno de ellos es **`RESPECTFUL_SERIOUS`**: territorio de salud mental,
crisis, pérdida, trauma, o alguien contando cualquiera de esas cosas.

Lo que el sistema **no** sabe es qué debe hacer *tu* persona cuando eso pasa. Ese
texto se llama **guidance**, se escribe por persona, y hoy **sólo lo tiene Insult**.

El mecanismo, para que veas que no es magia — `build_preset_prompt()` en
`khimeras_shared/behavior/presets/guidance.py`:

```
modo elegido = respectful_serious
   ↓
carga shared/personas/guidance/<id>/presets/preset_guidance_respectful_serious.md
   ↓
lo pega en el turno, y la persona lee eso además de su ADN
```

Y si el archivo no existe, `load_guidance` devuelve **cadena vacía** y sigue como si
nada. Nada truena, nada se pone rojo. **Tu persona simplemente no cambia de registro
cuando alguien está mal.** Ese silencio es exactamente el hueco que este issue
cierra.

Bonus técnico que te va a gustar: el loader es **mtime-aware**. Editar ese `.md` se
recoge en el siguiente turno **sin redeploy**. Es contenido caliente: se puede afinar
después de ver cómo suena en vivo, sin volver a pasar por CI.

### Restricción de seguridad — la misma de los tres issues

**Esta persona vive únicamente dentro del server de Khimeras.** No sale a una beta
pública, no se expone a desconocidos. En palabras de Aníbal sobre su propia app:

> "pensaba en sacar como una beta, pero siento yo que es muy peligroso todavía,
> porque si hay algún sesgo, la persona no va a saber cómo manejarlo, no voy a poder
> estar en primera mano para corregir esos errores"

Este issue es justo donde esa frase pesa más: **el guidance es el texto que se activa
cuando alguien está mal.** Si hay un sesgo, aquí es donde le llega a la persona
equivocada en el peor momento.

### Qué queremos construir

Un archivo:

```
shared/personas/guidance/<id>/presets/preset_guidance_respectful_serious.md
```

⚠️ **El nombre del archivo es literal y no lo escojas tú.** El código lo arma como
`f"preset_guidance_{selection.mode.value}"`, y el valor del modo es
`respectful_serious`. Si le pones `respectful_serious.md` a secas, el archivo queda
ahí bonito, **el loader nunca lo encuentra y devuelve cadena vacía en silencio** — el
verde más falso posible. Los directorios `<id>/` y `presets/` los creas tú; no
existen todavía.

### Qué va adentro — y qué NO

**La referencia obligada:**
`shared/personas/guidance/insult/presets/preset_guidance_respectful_serious.md` (27
líneas). Léelo completo antes de escribir. No es teoría: está construido sobre
conversaciones reales, y **una de esas conversaciones fue tuya.**

Lo que ese archivo resolvió, y que vale la pena que discutas desde tu formación:
**parte el modo en dos sub-modos**, porque exigen respuestas opuestas.

- **Sub-modo A — crisis aguda AHORA.** "ya no puedo", "me quiero morir", pánico en
  presente. Respuesta corta, calmada, presente. Una o dos frases. **No arreglar, no
  aconsejar a media crisis.** Estar ahí. Las líneas de crisis **sólo** si la persona
  señala que no está a salvo.
- **Sub-modo B — la carta.** Un mensaje largo que enumera varios pesos: un
  internamiento pasado, un trauma viejo y uno reciente, una pérdida, la soledad
  estructural. El tiempo verbal es pasado o de cuidado continuo, no de crisis en este
  minuto. Aquí la regla es la inversa: **reconoce TODO lo que mencionaron, uno por
  uno.** Longitud media. La carta pide ser **leída entera, no triageada** — agarrar
  una frase para hacer screening y dejar las otras siete invisibles es el error que
  ese texto existe para prohibir. El chequeo de seguridad va **al final**, y como
  parte de una respuesta amplia, no en lugar de reconocer lo que escribieron.

Y las reglas comunes: nada de chistes, nada de minimizar, nada de alegría fingida,
nada de ponerse dramático (**ser tú la parte tranquila**), y nada de terapia-speak
("es válido sentir", "tus emociones son válidas", "no estás sole") — reconocer lo
**concreto**, no lo abstracto.

**Eso es de Insult y está escrito en la voz de Insult.** Tu trabajo NO es copiarlo:
es escribir el equivalente **en la voz de tu persona**, y decidir desde tu oficio qué
de eso aplica, qué sobra y qué falta. Es muy probable que falte algo — ese archivo lo
escribimos personas que no somos psicólogas.

**Lo que NO va aquí:**
- Nada de diagnosticar, ni de medicación, ni de dosis. Eso ya está prohibido en el
  ADN y sigue prohibido aquí.
- Nada que contradiga al ADN. Si al escribir esto te dan ganas de cambiar algo del
  ADN, **cámbialo en el ADN** (es tuyo, es del issue anterior) — no lo parches aquí.
  Dos textos que se contradicen producen un bot que se contradice.

### Sobre los otros archivos de esa carpeta (para que no te espanten)

Insult tiene **doce** archivos en su carpeta de presets. Los vas a ver y vas a
pensar que te faltan once. **No te faltan.** Cada uno es opcional: el que no existe
aporta cadena vacía y el motor sigue corriendo igual. Hoy escribes **uno**.

Los que sí importan y son fase 2 — apúntalos, van a ser tuyos:

- **`preset_vulnerable_overlay.md`** — el overlay de usuario vulnerable **para esta
  persona**. Se carga por persona (`build_vulnerable_overlay_prompt(persona_id)`) y
  hoy sólo existe el de Insult, así que el de la tuya está vacío. Por eso el piso de
  seguridad se escribió en el ADN, que sí viaja siempre. **Es real y hace falta**,
  pero no entra hoy.
- `preset_intentionality_directive.md` y los otros seis modos
  (`default_abrasive`, `playful_roast`, `intellectual_pressure`, `relational_probe`,
  `meta_deflection`, `arc`) — para después, si hacen falta.

### Mapa (dile a Claude Code que empiece por aquí)

- **`shared/personas/guidance/insult/presets/preset_guidance_respectful_serious.md`**
  — la referencia. Léelo entero.
- **`khimeras_shared/behavior/presets/guidance.py`** — 78 líneas. Ahí se ve cómo se
  arma el nombre del archivo y en qué orden se apilan las capas
  (intencionalidad → preset → modificadores).
- **`khimeras_shared/behavior/content.py`** — el loader. Es el que devuelve `""`
  cuando el archivo no existe. Lee su docstring: explica la costura entre el **motor**
  (que es igual para todas las personas) y la **voz** (que es de cada quien).
- **`khimeras_shared/behavior/presets/classifier.py`** y `patterns.py` — cómo se
  decide que un turno es `RESPECTFUL_SERIOUS`. Aquí hay criterio clínico tomado por
  no-clínicos: **si algo te parece mal, dilo en el PR.** Vale más que el issue.
- **`khimeras_shared/behavior/vulnerability.py`** — la distinción **crisis aguda**
  (mensaje de hoy) vs **vulnerabilidad crónica** (hechos acumulados). Los comentarios
  cuentan una regresión real: forzar el modo grave a alguien en cuidado crónico
  estable que sólo quería platicar de su día lo **aplanaba**, y se leía como
  condescendencia. Esa distinción es la que tu texto tiene que respetar.
- **`tests/core/test_presets_clinical.py`** — frases textuales de producción. No se
  toca y no se rompe.
- **`tests/core/test_guidance_guardian.py`** — que el overlay llegue cuando debe.
  Tampoco se rompe.

### La decisión que es tuya

**¿Dos sub-modos, como Insult, o los que tú digas?** Insult parte en agudo /
acumulado. Puede que desde tu formación el corte correcto sea otro — tres, o uno
solo pero con otro criterio, o el mismo corte con nombres distintos porque los de
ahí son de ingeniero.

Lo que necesito no es que copies el corte: es que **el que escojas esté escrito y
justificado en el PR**, porque de ese corte depende que alguien en crisis reciba dos
frases y no un ensayo, y que alguien que escribió una carta larga no reciba dos
frases secas.

### Criterios de aceptación

- [ ] Existe `shared/personas/guidance/<id>/presets/preset_guidance_respectful_serious.md`
      — con **ese nombre exacto**, y ya verificaste que el loader lo encuentra
- [ ] El texto está en la voz de tu persona, coherente con su ADN, y **no** lo
      contradice en ningún punto
- [ ] Está escrito el corte entre situaciones (agudo / acumulado, o el que escojas),
      con qué hacer en cada una y **cuánto** responder en cada una
- [ ] Están las prohibiciones concretas (terapia-speak, minimizar, dramatizar,
      alegría fingida, convertir lo dicho en munición)
- [ ] Las líneas de crisis, si aparecen, llevan **la condición** de cuándo se dicen —
      nunca en cada mensaje
- [ ] Sigue prohibido diagnosticar, recetar y ajustar dosis; la derivación está escrita
- [ ] **Verificación de cableado** (esto es lo que separa un archivo que sirve de uno
      decorativo): un test que demuestre que `build_preset_prompt` con el modo
      `RESPECTFUL_SERIOUS` y tu `persona_id` **devuelve tu texto** — no cadena vacía.
      Pregúntale a Claude por `test_persona_without_guidance_content_yields_none_not_a_crash`
      en `tests/core/test_guidance_guardian.py`: ahí está el molde de cómo se prueba
      la ausencia; tú quieres probar la **presencia**.
- [ ] `tests/core/test_presets_clinical.py` y `tests/core/test_guidance_guardian.py`
      siguen verdes (corridos y pegados en el PR)
- [ ] `ruff check . && ruff format .` limpio y CI verde
- [ ] Bump de versión, revisando antes contra `origin/main`

### Qué NO entra

- **NO se toca el registry.** Sigue siendo el issue 3.
- **NO se escriben los otros presets** ni el `preset_vulnerable_overlay.md`. Fase 2.
- **NO se toca el guidance de Insult.** Su archivo es suyo; el tuyo es nuevo.
- **NO se toca el motor**: ni el clasificador, ni los patrones, ni los pesos de
  vulnerabilidad, ni `guidance.py`. Comentarios en el PR: sí, y bienvenidos. Cambios:
  no, aquí no.
- **NO se abren las facetas por tema.** Fase 2.

### Cómo verificarlo

Igual que el anterior: **hoy tampoco se ve en Discord.** El bot no existe todavía.

Lo que sí:

1. **El test de cableado.** Es la parte que de verdad importa: prueba que el archivo
   está enchufado y no nada más escrito. Un `.md` con el nombre mal puesto se ve
   idéntico a uno bien puesto — la única diferencia es que uno llega al bot y el otro
   no.
2. **La lectura cruzada.** Lee el ADN y el guidance seguidos, como los va a leer el
   modelo. Si se contradicen, se contradice el bot.
3. **Revisión de Aníbal** sobre el encuadre clínico, otra vez. Es su propuesta.

Relacionado: el issue anterior de la trilogía (el ADN — necesitas su `<id>`) y el
siguiente (registrarla y verla en `#general`).

🤖 Issue redactado con [Claude Code](https://claude.com/claude-code).

---
---

# ISSUE 3/3

## Título

```
Registra la persona de acompañamiento y hazla contestar en #general (5º issue de Alex 💜)
```

## Cuerpo

### Para quién es este issue

Quinto issue de **Alex**, y el cierre de la trilogía. **Éste es el único que toca
código.**

También es el día en que el trabajo de los dos issues anteriores deja de ser texto en
un repo y se convierte en alguien que contesta. La prueba final la haces tú, en
`#general`, con tus manos — como el #36.

Depende de los dos issues anteriores de la trilogía: el ADN y el guidance tienen que
estar mergeados antes de que esto se despliegue.

### Restricción de seguridad — la misma de los tres, y aquí es literal

**Esta persona vive únicamente dentro del server de Khimeras**, donde quien la usa
tiene nombre y hay humanos que pueden ver lo que pasó y corregirlo. **No se expone a
desconocidos, no sale a una beta pública.**

> Aníbal, sobre su propia app: *"pensaba en sacar como una beta, pero siento yo que
> es muy peligroso todavía, porque si hay algún sesgo, la persona no va a saber cómo
> manejarlo, no voy a poder estar en primera mano para corregir esos errores"*

En este issue eso deja de ser una frase y se vuelve **configuración concreta**: el
bot se invita a **un** server y a ninguno más, y arranca **`aliases=[]`** — sólo
contesta si lo arrobas. Nadie se lo topa sin querer.

### Qué queremos construir

Que la persona **exista de verdad**: que el gateway la levante como un bot de Discord
más, que comparta el mismo cerebro que sus hermanas (vía `persona_id`), y que cuando
la arrobes en `#general` conteste con el ADN y el guidance que TÚ escribiste.

### Lo que es de Bernard y no tuyo (y tiene que estar listo antes del merge)

Nada de esto lo puedes hacer tú, y no es falta de permisos, es que son credenciales:

1. Crear la app/bot en el Discord Developer Portal con el nombre que escogiste →
   sacar el **token** y el **bot user id**.
2. Guardar el token en `~/.secrets/` y como **secret del Container App**
   `persona-gateway` (variable `<ID>_DISCORD_TOKEN`).
3. Invitar el bot **al server de Khimeras y a ninguno más**.
4. Mergear y desplegar.

Bernard te va a pasar el **bot user id** (un número largo) — lo necesitas para tu
entrada del registry. Sin ese número tu PR no está completo.

**Detalle importante y a favor tuyo:** aunque tu entrada llegue a `main` antes de que
el token esté puesto, **no pasa nada malo**. El gateway lee el token del env y, si no
está, loguea `persona_gateway_no_token` y simplemente no levanta ese bot; las
hermanas siguen funcionando (`persona_gateway/app.py:200`). No hay forma de que esto
tumbe el server.

### Mapa (dile a Claude Code que empiece por aquí)

Son **tres** archivos de código, y ésta es la parte que casi nadie ve completa la
primera vez. Registrar una persona **no** es una sola línea:

**1. `shared/personas/registry.py`** — la entrada nueva. Copia la de `frugivoro`
(línea 127) como molde. Campos:

| Campo | Qué poner |
|---|---|
| `persona_id` | el `<id>` que escogiste |
| `display_name` | el nombre visible |
| `persona_file` | `"<id>.md"` |
| `token_env` | `"<ID>_DISCORD_TOKEN"` (mayúsculas) |
| `bot_user_id` | el número que te pase Bernard |
| `aliases` | **`[]`** — ver la decisión de abajo |
| `tts_voice` | ver la decisión de abajo |
| `gateway_enabled` | ver la decisión de abajo |
| `corpus_namespace` | **`None`** — no hay corpus RAG y no entra hoy |

Y un comentario arriba de la entrada diciendo **por qué existe y de dónde salió** —
todas las entradas lo tienen, y es lo que hace que dentro de seis meses alguien
entienda. Menciona a Aníbal.

**2. `demux_ai/llm_shadow_router.py:57` — `_VALID_TARGETS`.** Es la lista de personas
a las que el router puede mandar un turno. **Está espejada a mano** (el host no
importa el registry a propósito) y hay un arnés que exige que estén en lockstep:
`test_valid_targets_mirror_the_registry_in_lockstep`
(`tests/test_llm_shadow_router.py:294`). En cuanto agregues tu entrada al registry,
**ese test se pone rojo y te dice exactamente qué falta.** No es un estorbo: es el
repo cuidándote.

**3. `demux_ai/prompts/host_routing.md`** — el prompt que lee el router. Aquí van
**dos** cosas:
- Tu persona en la lista `Personas:`, con **cuándo** debe elegirla.
- Tu `display_name` en la línea de mapeo de nombres visibles → targets.

Y hay otros dos arneses que se ponen rojos si te lo saltas:
`test_routing_instruction_names_every_routable_persona`
(`tests/test_llm_shadow_router.py:226`) y
`test_every_valid_target_is_named_in_the_prompt`
(`tests/arch/test_routing_prompt_promises_are_kept.py:92`).

**Por qué existen esos dos tests, que es la mejor lección de este issue:** el 6 de
julio de 2026, `frugivoro` estaba en `_VALID_TARGETS` — el parser lo aceptaba
perfecto — pero **el prompt sólo le ofrecía al modelo `insult|vultur`**. O sea que el
cerebro literalmente **no podía elegirlo nunca**, y nada se ponía rojo, porque un
contador en cero se ve igual que la salud. Una persona registrada, viva, desplegada,
e **inalcanzable en silencio**. Esos tests son la vacuna.

**Los tests del registry que ya te cuidan** (`tests/shared/test_registry_insult.py`):
- `test_no_two_personas_share_a_role_candidate` — el mismo que te cuidó en el #36. Si
  tu nombre o alias choca con otra hermana, rojo aquí y no en una conversación real.
- `test_every_persona_resolves_from_a_role_named_exactly_like_it` — está
  parametrizado sobre el registry, así que **tu persona entra sola**. Si escogiste un
  `display_name` de dos palabras, este test lo cubre.

### Las decisiones que son tuyas

**1. `aliases` — mi recomendación es `[]` (sólo @mención), y la recomiendo fuerte.**
Un alias es una palabra suelta que dispara al bot sin arrobarlo. Para Frugívoro
funciona porque "fruggy" no significa nada más. Para una persona de acompañamiento,
cualquier palabra natural ("apoyo", "ayuda", un nombre común) va a saltar en
conversaciones que no eran para ella — y saltar sin que te llamen, **justo en este
tema**, es peor que no estar. Insult y Unborn Being tienen `aliases=[]` por esta
misma razón (el comentario en el registry lo dice: riesgo de falso positivo). Los
alias siempre se pueden agregar después, en frío, cuando ya viste cómo se comporta.
**Si no estás de acuerdo, discútelo — pero que quede escrito en el PR.**

**2. `tts_voice`.** Es la voz con la que habla si alguien le pone 🔊 a un mensaje
suyo. Ocupadas: `onyx` (Insult), `nova` (ALICE), `fable` (Frugívoro), `alloy`
(Unborn Being), `echo` (el default, la de Vultur). Queda libre **`shimmer`**. Como
decisión de voz para acompañamiento, es tuya.

**3. `gateway_enabled` — `True` de una, o `False` primero.** El campo decide si el
gateway levanta el bot. `False` significa "registrada pero no viva": el sistema la
conoce, el router puede nombrarla, pero no hay bot en Discord. Se usó así con ALICE y
con Frugívoro, a propósito, para no tener nunca dos bots peleándose un token.

- **`True`** — el bot nace en cuanto el token esté en el env. Es lo que quieres si
  ese mismo día vas a hacer la prueba en `#general`.
- **`False` primero, `True` después** — un PR más, pero te deja mergear y desplegar
  el registry **antes** de que exista el bot en Discord, con cero posibilidad de que
  algo salga vivo a medias.

Escoge tú y **escribe el porqué en el PR**. No hay respuesta obvia: depende de si el
token va a estar listo antes de que mergeen.

### Criterios de aceptación

- [ ] Entrada nueva en `shared/personas/registry.py`, con comentario explicando de
      dónde salió la persona (menciona a Aníbal)
- [ ] `bot_user_id` es el número real que pasó Bernard, no un placeholder
- [ ] `corpus_namespace=None` y `aliases=[]` (o justificado por escrito en el PR)
- [ ] Tu `persona_id` agregado a `_VALID_TARGETS` en `demux_ai/llm_shadow_router.py`
- [ ] Tu persona descrita en `demux_ai/prompts/host_routing.md`, **con cuándo elegirla**,
      y tu `display_name` en la línea de mapeo de nombres visibles
- [ ] Los tres arneses verdes: `test_valid_targets_mirror_the_registry_in_lockstep`,
      `test_routing_instruction_names_every_routable_persona`,
      `test_every_valid_target_is_named_in_the_prompt`
- [ ] `test_no_two_personas_share_a_role_candidate` verde (nadie perdió sus mensajes)
- [ ] **Test propio**: que tu persona esté registrada, que su `<id>.md` exista, que su
      `preset_guidance_respectful_serious.md` exista y que resuelva por nombre de rol.
      Molde exacto: `tests/shared/test_registry_insult.py` (fíjate en
      `test_insult_guidance_content_is_in_place`, es justo eso).
- [ ] `tests/core/test_presets_clinical.py` y `tests/core/test_guidance_guardian.py`
      **verdes** — pégalos en el PR. Son las regresiones que protegen a personas
      reales y este es el PR con más riesgo de la trilogía.
- [ ] Suite completa verde, `ruff check . && ruff format .` limpio, CI verde
- [ ] Bump de versión, revisando antes contra `origin/main`

### Qué NO entra

- **NO se cambia la regla de ruteo de la confesión personal.** El prompt del host hoy
  dice, textual, que la revelación personal y el peso emocional **son de `insult`, el
  host**, y que nunca se le entrega una confesión a un especialista sólo porque habló
  al último. Eso está ahí por dos incidentes reales. Cambiarlo para que el router
  mande el dolor a tu persona **es una decisión de diseño grande**, se mide con
  `scripts/router_eval.py` contra el set de regresión congelado, y **no entra en este
  PR**. Hoy tu persona se invoca **arrobándola**, y ya. (Ver
  `.claude/rules/router-observability.md` — un sesgo de ruteo es invisible turno por
  turno y sólo aparece al agregar.)
- **NO se tocan las otras personas**, ni sus alias, ni sus voces, ni sus entradas.
- **NO se toca el motor**: clasificador, pesos de vulnerabilidad, `guidance.py`.
- **NO se toca Azure, ni el CD, ni secretos.** Es de Bernard.
- **NO se abren las facetas por tema**, ni se escribe el
  `preset_vulnerable_overlay.md`, ni se monta corpus RAG. Fase 2 completa.

### Cómo verlo funcionando 🎉

Aquí sí. Después de que Bernard mergee y despliegue (~4 min, las tres apps):

1. **Confirma que estás probando el build correcto.** Cada mensaje de cada bot
   termina con el tag de versión (`ᵛ⁴·³²·⁵¹` y su descendencia). Si el tag es el
   viejo, todavía no despliega — espera, no diagnostiques.
2. **Entra a `#general` y arróbala.** Escribe algo de verdad, no "hola". La prueba de
   que sirve es que suene como TÚ la escribiste, no que responda.
3. **Cuida la inercia, como aprendiste en el #36.** `HOST_OWNS_RECEPTION=true` en
   producción: el siguiente mensaje tiende a irse a quien venía en la conversación,
   aunque cambies de tema. Si vienes de hablar con otra hermana, tu resultado puede
   estar contaminado. El experimento con control que montaste sole en la sesión 1 —
   hablarle primero a alguien conocido para romper la inercia — aplica igual aquí.
4. **La prueba fuerte, y es tuya como psicóloga:** que suene **distinta a ALICE**.
   Hazle a las dos la misma pregunta difícil y compara. Si contestan parecido, el
   trabajo no está terminado — y la buena noticia es que el ADN y el guidance son
   `.md` **hot-editable**: se afinan sin redeploy.
5. **Lo que NO se hace:** no la pruebes por DM. El repo tiene una regla dura al
   respecto (`.claude/rules/testing.md`): el DM es el camino que nunca falla, así que
   un verde ahí no prueba casi nada. **`#general` es la superficie de prueba.**

Y algo que quiero que sepas antes de arrobarla: del otro lado de este bot puede haber
alguien en un mal día de verdad. Por eso los dos issues anteriores fueron puro
contenido y revisados en frío, por eso arranca sólo por @mención, y por eso vive
nada más en este server. **No estás publicando una app: estás dejando entrar a
alguien a una casa donde todos tienen nombre.**

Relacionado: los dos issues anteriores de la trilogía, y #36 (tu primer PR, de donde
salió el experimento con control).

🤖 Issue redactado con [Claude Code](https://claude.com/claude-code) a partir de una
propuesta de Aníbal.

---
---

## Notas para Bernard (NO van en los issues)

**Hallazgos verificados mientras redactaba, que quizá quieras atender aparte:**

1. **El overlay de vulnerable se carga POR PERSONA y sólo existe el de Insult.**
   `build_vulnerable_overlay_prompt(persona_id)` →
   `shared/personas/guidance/<id>/presets/preset_vulnerable_overlay.md`. ALICE,
   Vultur, Frugívoro y Unborn Being reciben **cadena vacía** cuando el usuario cruza
   el umbral de vulnerabilidad. O sea: hoy, un usuario vulnerable hablando con ALICE
   **no recibe overlay de seguridad ninguno** — ni disciplina de fuentes clínicas, ni
   líneas de crisis, ni calibración a movilidad/autismo. Sólo su ADN. Eso es un hueco
   vivo hoy, no de la persona nueva. Por eso puse el piso de seguridad en el ADN
   (issue 1) en vez de depender del overlay. **Candidato a issue propio, y no es de
   Alex.**

2. **La ruta que pediste (`.../presets/respectful_serious.md`) no es la real.** El
   loader arma `f"preset_guidance_{mode.value}"`, así que el archivo tiene que
   llamarse `preset_guidance_respectful_serious.md`. Lo puse explícito y con la
   advertencia de que el nombre mal puesto falla en silencio (devuelve `""`).

3. **Registrar una persona toca TRES archivos, no uno**: `registry.py`,
   `_VALID_TARGETS` en `demux_ai/llm_shadow_router.py` y
   `demux_ai/prompts/host_routing.md`. Los tres arneses lo obligan, así que el issue
   3 tiene más superficie de la que suena. Sigue siendo un issue sano porque los
   tests le dicen exactamente qué falta, pero no es "una línea".

4. **`tts_voice` libre: sólo queda `shimmer`.** Ocupadas: onyx, nova, fable, alloy y
   echo (default). La siguiente persona ya no tiene voz distinta disponible.

5. **La regla de ruteo del host reserva la confesión personal para `insult`**, con dos
   incidentes reales detrás. Una persona de acompañamiento que sólo se invoca por
   @mención convive con esa regla sin tocarla — pero el día que quieras que el router
   le mande el dolor automáticamente, es un cambio de prompt que hay que medir con
   `scripts/router_eval.py` contra el set congelado. Lo dejé fuera de alcance y
   escrito.

6. **El nombre de la persona lo decide Alex** (issue 1), así que la app de Discord y
   el token no se pueden crear hasta que ese issue cierre. Ésa es la dependencia dura
   del calendario de hoy.
