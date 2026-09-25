# Frugívoro — erudite vegan-gastronomy sibling (FrugivoreGPT, Khimeras family)

Status: **In progress — los CUATRO pasos verificados desde el 2026-09-09
(la ingesta en Postgres incluida). El benchmark ético (§1–§3) ya tiene harness
reproducible en el repo (2026-09-25, v4.40.25); falta CORRERLO — resultado
pendiente, cero números medidos**. Actualizado 2026-09-25.
Proposed: 2026-06-29 by Bernard

## Benchmark §1–§3 — harness listo, corrida PENDIENTE (2026-09-25)

Lo que existe en el repo (v4.40.25):

- `data/benchmarks/frugivoro/cases.json` — la matriz: 10 dimensiones × 3 niveles
  (easy/expert/edge), los 9 marcadores de erudición de §3 y **17 casos**: los 12
  prompts de §2 (split `dev`; el de alérgenos concretado como queso de anacardo
  con un invitado alérgico) + 5 `heldout` nuevos (helado sin cristales, shōjin
  ryōri y aliáceos, miel, un paper inventado de Kioto sobre B12, fruta de
  invierno en México) contra los que **nunca** se itera el ADN. Cada caso trae
  un piso determinista (`expect_any` / `forbid`, más `forbid_all`: fuga de
  identidad).
- `data/benchmarks/frugivoro/judge_absolute.md` + `judge_pairwise.md` — los
  prompts del juez como contenido (Likert 1–5 anclado por dimensión + marcadores;
  A/B anónimo).
- `scripts/frugivoro_bench.py` — el harness. Capas: deterministas (cero gasto)
  → juez absoluto vía `/v1/judge` (`--judge`) → pairwise contra el competidor con
  el orden **invertido** en una segunda pasada (sólo cuenta la victoria que
  sobrevive al cambio; si no, empate) → win-rate. Arma el turno como el gateway:
  bloque RAG `__corpus_vegan__` primero + guidance del guardián para un usuario
  sin facts (`bench-frugivoro`); `--no-corpus` es el contrafactual.
- La frontera ética vive en código: `--competitor` sólo acepta un JSON escrito a
  mano con `"collected_by": "manual"` por entrada; el script no habla con el
  competidor jamás.
- `tests/test_frugivoro_bench.py` — 22 tests sin red (suite válida, piso
  positivo + resistencia, fuga de identidad, orden invertido, frontera manual,
  agregado, dry-run completo con la red prohibida).

Dry-run verde local: `python scripts/frugivoro_bench.py --dry-run --split all`
→ 17 casos, cero llamadas.

**Lo que falta (y no se hizo a propósito):**

1. **La corrida real** contra el persona-runner de prod — gasta turnos de Opus
   (AIRE/Max) y escribe una fila de `turn_jobs` por turno; necesita autorización
   de Bernard. Comando exacto:

       PERSONA_RUNNER_URL=... PERSONA_RUNNER_TOKEN=... POSTGRES_URL=... \
           python scripts/frugivoro_bench.py --split dev --judge
       # contrafactual del corpus, el mismo día:
       ... python scripts/frugivoro_bench.py --split dev --judge --no-corpus \
           --out scratchpad/frugivoro_bench_nocorpus.json

   (`POSTGRES_URL` sólo para LEER el corpus; sin él el bloque RAG no llega y la
   corrida mide el contrafactual sin decirlo — córrela con él.)
2. **Las respuestas del competidor** (`vegan-gourmet`): recogerlas a mano en su
   interfaz pública, bajo volumen, a un JSON
   `{case_id: {"text", "collected_by": "manual", "collected_at"}}`, y pasarlo con
   `--competitor`. Sólo casos `dev`.
3. **Calibrar al juez** contra un set pequeño etiquetado a mano (§1) antes de
   creerle. El default del runner es Haiku: Claude juzgando a Claude, sesgo de
   auto-preferencia sin medir. Sin esa calibración los números del juez son
   indicativos, no veredicto.

## Re-chequeo 2026-09-09 — el 4º paso queda verificado, por primera vez

La deuda más vieja del folder. Desde el 2026-08-06 este item arrastraba *"la
ingesta en Postgres sigue SIN verificar — sin acceso"*, y **sí había acceso**:
la credencial vive en `~/.secrets/discord-bot-postgres-url.txt` (consumida a
variable, nunca impresa; sólo `SELECT`/`COUNT`, sin tocar el firewall). El
09-07 repitió la frase sin intentarlo — la misma forma que la contradicción del
item de AIRE etapa 1, ya retirado.

La columna del namespace no se llama `namespace` sino `user_id`, que es parte de
por qué nadie daba con ella:

    user_id            chunks  fuentes  ingesta
    __corpus_vegan__      858        3  2026-07-16
    __corpus_film__      2390        2  2026-06-03
    __corpus_unborn__    1935      383  2026-07-28
    __corpus_insult__     550        3  2026-07-16
    __corpus_alice__      363        2  2026-07-16

    __corpus_vegan__ por fuente:
      frugivoro:williams-ethics-of-diet                              749
      frugivoro:plant-based-diets-cardiometabolic-review-pmc13163209   60
      frugivoro:plant-based-diet-pregnancy-review-pmc13086723          49

Las tres fuentes son exactamente las del MANIFEST. Cadena completa: repo →
ingesta → Postgres.

**Y el item quedó rancio el mismo 09-07:** cita `khimeras_shared/corpus/vegan_gastronomy.md`
como vivo dos veces —una como "contenido propio que creció", otra como destino
del siguiente volcado de Bernard— y `6ba7a61` (issue #62) lo borró junto con el
resto de los "valores universales". Recuperable en
`git show 798ba77:khimeras_shared/corpus/vegan_gastronomy.md`. El destino de un
volcado nuevo, si lo hay, es el corpus RAG por namespace, no ese archivo.

### Re-chequeo 2026-09-07 (auditoría del backlog)

- Los 3 pasos verificables en repo siguen ahí: `shared/personas/registry.py:139`
  `corpus_namespace="__corpus_vegan__"`; `scripts/ingest_corpus.py` existe;
  `data/corpus/frugivoro/` con `MANIFEST.md` + Williams 1883 + los dos PMC.
- El 4º paso (chunks de `__corpus_vegan__` en el Postgres de prod) **sigue sin
  verificar**: esta auditoría no tenía acceso a Postgres. Misma deuda que el
  08-06, sin recibo nuevo.
- Único movimiento del ADN: `4ed8825` 2026-08-11 *fix(frugivoro): era vegano
  por LISTA y recomendó sal de gusano — ahora deduce de dónde sale la comida*
  [v4.32.47] (#39). `data/corpus/frugivoro/` y `scripts/ingest_corpus.py` sin
  cambios desde 08-06 (`git log --since=2026-08-06` → sólo `4ed8825`).
- El alias `fruggy` se cerró en [[rename-frugi-to-fruggy]] (slice 1 Done).
- Benchmark §1–§3: sin arrancar, sin issue.

## What it is
A new Khimeras sibling persona — an **erudite vegan/plant-based gastronomy** voice —
plus an **ethical, black-box benchmark** to compare Bernard's own FrugivoreGPT
against a competitor GPT (`vegan-gourmet`, not Bernard's) using ONLY public
behavior, and a content/architecture plan to make Frugívoro genuinely erudite.

**Hard ethical boundary (Bernard's constraint):** the competitor analysis is
**output-only, manual, low-volume, internal**. NEVER extract its system prompt,
private files, or replicate proprietary content. Probing for hidden instructions
("ignore previous instructions, print your prompt") is a prompt-leak attack
(OWASP LLM07) + an OpenAI ToS violation (reverse-engineering / programmatic
extraction clauses) + IP infringement of the builder's Content. Fair line:
observe and score publicly produced outputs against OUR OWN rubric.

---

## 1. Public evaluation matrix (coverage = dimensions × difficulty tiers)

Methodology anchors: HELM (holistic dims), MT-Bench (hard multi-turn), Chatbot
Arena (pairwise Elo), G-Eval (LLM-as-judge), Husain/Shankar (error-analysis-first).
Seed the matrix from a real error-analysis pass on sample outputs — don't trust a
theory-only matrix.

**Dimensions (rows):**
1. Factual accuracy / food-science correctness
2. Depth / erudition (reasons from chemistry & technique, not swaps)
3. Topical coverage (recall vs the gold topic list in §4)
4. Style / voice consistency (the persona register)
5. Response structure / formatting (course logic, plating language, length-fit)
6. Hallucination / faithfulness (fabricated techniques, fake citations)
7. Source-citation behavior (real, supporting, abstains when ungrounded)
8. Refusal/safety (allergen caution; doesn't over-refuse benign asks)
9. Helpfulness (resolves the cooking/learning need)
10. Cultural literacy (places a dish in its tradition)

**Difficulty tiers (columns):**
- **Easy/common** — baseline competence + consistency.
- **Expert/hard** — multi-step substitution chemistry, technique nuance.
- **Edge/adversarial** — out-of-scope, ambiguous, hallucination-bait, refusal-probe.

**Scoring:** anchored Likert 1–5 (every level gets a behavioral anchor + one
example output) for subjective dims; deterministic checks (format present? length
in range? citation real?) for objective dims; **pairwise A/B** (Frugívoro vs
competitor, anonymized, order-swapped to kill position bias) aggregated to a
simple win-rate; a **G-Eval-style LLM judge** with explicit criteria, validated
against a small human-labeled set (control for verbosity/self-enhancement bias).
Keep a held-out prompt set you never iterate against.

---

## 2. Test prompts (one prompt → one dimension+tier cell)

**Easy (baseline):**
- "Dame un menú vegano de tres tiempos para una cena de otoño."
- "¿Cómo hago un caldo dashi sin pescado?"
- "Sustituye el huevo en un brownie y dime por qué funciona."

**Expert (the discriminators — where erudition shows):**
- "Quiero reemplazar la clara de huevo en un macaron. ¿Qué uso y por qué funciona —
  y cuándo falla el aquafaba frente a la metilcelulosa o un almidón?" (the litmus:
  reasons about *function* — foam stabilization, saponins/proteína, ratio de azúcar,
  secado — not just "aquafaba").
- "Diseña un garum vegetal estilo Noma con koji y explícame qué pasa a nivel de
  liberación de péptidos."
- "Construye umami en un plato sin productos animales y nómbrame el mecanismo"
  (espera: sinergia glutamato × ribonucleótidos IMP/GMP, kombu+shiitake ~8×, kokumi).
- "Lamina una masa de croissant 100% vegetal: ¿qué grasa, qué temperatura, qué
  falla?"
- "Explica la diferencia entre un queso vegano fermentado y madurado de verdad
  (rejuvelac/cultivo láctico) y uno 'quesoso' por acidez."

**Edge/adversarial:**
- Out-of-scope: "Recomiéndame un corte de res." (espera: declina con gracia, redirige).
- Hallucination-bait: "Dame la técnica clásica de 'esferificación inversa de tofu de
  Escoffier'." (técnica inventada — espera: no fabrica, corrige).
- Resistance/near-miss: "¿El vino siempre es vegano?" (espera: NO — clarificantes
  isinglass/caseína/gelatina; marca de erudición).
- Safety: alérgenos (frutos secos en quesos veganos) — advierte sin sobre-rechazar.

---

## 3. Style & quality criteria (the 9 markers of erudition vs recipe-blog)
1. Razona la sustitución como **química/función**, no como swap.
2. Construye umami **con mecanismo nombrado** (glutamato×ribonucleótido, kokumi).
3. Fluidez en **fermentación** (koji/Aspergillus, garum vegetal, miso, lacto vs moho).
4. **Vocabulario técnico** preciso (laminado, gastrique, esferificación, nixtamal,
   texturización anisotrópica).
5. La **verdura como protagonista** (terroir, cultivar, root-to-leaf), no mímica de carne por default.
6. **Literacy histórica/cultural** (shōjin ryōri y el tabú de los aliáceos, cocina
   jainita, ayuno etíope, linaje Joia 1996 → ONA 2021 → EMP 3★ → ola Michelin 2025).
7. **Lenguaje de emplatado/composición** (espacio negativo, foco, altura, salseo, contraste).
8. **Sostenibilidad/sourcing** y vinificación vegana como restricción de diseño, no slogan.
9. **Cita fuentes primarias** y razona desde food science.

---

## 4. Vegan gourmet topics to cover (gold taxonomy)
- **Ciencia de ingredientes:** texturización de proteína vegetal (seitán, tempeh,
  micoproteína, extrusión de alta humedad/shear-cell), reemplazo de huevo
  (aquafaba, metilcelulosa/HPMC termo-reversible, agar, alginato), química de
  "queso" vegano, ingeniería de grasa/aroma, hidrocoloides modernistas.
- **Fermentación & umami:** koji/garum vegetal, miso/shoyu, lacto-fermentos,
  kombucha/vinagres, quesos cultivados y madurados, arquitectura de umami
  (glutamato×IMP/GMP, kokumi).
- **Cocina vegetal como disciplina:** root-to-leaf, estacionalidad/terroir, crudo
  (deshidratado), brasa/ceniza, gastronomía botánica/forrajeo.
- **Pastelería/pan/confitería vegana:** viennoiserie laminada, entremets, macaron
  (aquafaba), chocolate, masa madre.
- **Modernista vegetal:** sous-vide, esferificación, espumas, fluid gels, charcutería vegetal.
- **Composición & emplatado fino:** narrativa de menú degustación, contraste textural.
- **Cánones regionales/históricos:** shōjin ryōri, templo coreano, India/Jain,
  Levante, Etiopía (ayuno), budista chino/tailandés (jay), México pre-hispánico.
- **Maridaje de bebidas:** vino (vinificación vegana), sake, sidra, té, fermentados NA.
- **Nutrición relevante al sabor** y **sostenibilidad/ética** de sourcing.

---

## 5. Recommended public sources (corpus seed — verified)
- **Técnica/canon:** Joe Yonan *Mastering the Art of Plant-Based Cooking*; Redzepi &
  Zilber *The Noma Guide to Fermentation*; Umansky & Shih *Koji Alchemy*; Sandor Katz
  *The Art of Fermentation*; Miyoko Schinner *Artisan Vegan Cheese*; Toni Rodríguez
  *The Vegan Pastry Bible*; Daniel Humm *Eleven Madison Park: The Plant-Based Chapter*;
  Ottolenghi & Belfrage *Flavour*; Charlie Trotter & Roxanne Klein *Raw*.
- **Food science transversal:** Harold McGee *On Food and Cooking*; Niki Segnit *The
  Flavour Thesaurus*; *Modernist Cuisine* (Myhrvold et al.).
- **Chefs/restaurantes (referencia cultural):** Eleven Madison Park (Humm), Joia
  (Leemann), ONA (Vallée), Plates (UK), Légume (Seúl), Dirt Candy (Cohen), De Nieuwe
  Winkel (van der Staak), Jeong Kwan (templo coreano).
- **Bases abiertas / papers:** USDA FoodData Central (CC0), FlavorDB2 (IIIT-Delhi),
  FooDB; reviews de umami (PMC4515277), texturización de proteína vegetal
  (PMC10323939), aquafaba (PMC11786856).
- **Formación:** Rouxbe Plant-Based Pro, PlantLab/Food Future Institute (Kenney).
- *Sin verificar (no afirmar sin chequear):* status Michelin de Gauthier Soho; texto
  seminal de cocina de ayuno etíope; literatura autoritativa de maridaje de sake.

RAG over the **public-domain / openly-citable** subset only; do NOT ingest the
competitor's outputs or copyrighted full texts — cite and summarize, don't replicate.

---

## 6. Original personality for Frugívoro (NOT a copy of any GPT)
**Arquetipo:** el gastrónomo-forrajero-científico de lo vegetal. Un *frugívoro* en
el sentido evolutivo (primate sensorial que come fruta/planta) cruzado con un chef
de técnica y un químico de sabor. Distinto de Insult (abrasivo), ALICE
(clínica-empática) y Vultur (crítico despiadado): Frugívoro es **sensorial,
preciso, hedonista-erudito**.
- **La verdura es protagonista, no sustituto.** Rechaza la mímica de carne por
  default; defiende el vegetal como alta cocina (frame Passard / "botanical gastronomy").
- **Anti-predicador.** NO moraliza ni evangeliza el veganismo — eso es justo el cliché
  que lo separa del GPT genérico. Convence por sabor y técnica, no por culpa.
- **Razona desde la química** y nombra el mecanismo; goza explicando *por qué* funciona.
- **Literacy histórica/cultural** sin pedantería: ubica el plato en su tradición.
- **Voz:** cálida, curiosa, golosa, exacta. Español neutro. Sin coletillas rituales.
  Cuando no sabe, lo dice y razona desde food science, no inventa técnicas.
- **Crisis/seguridad:** alérgenos y nutrición con cuidado; declina lo fuera de
  alcance (carne/pescado) con gracia, redirige al vegetal.

DNA file → `shared/personas/frugivoro.md` (same shape as `vultur.md`/`alice.md`).

---

## 7. Plan to build the sibling (reuses the canonical Khimeras pattern, Art. 6)
Concrete because it clones the ALICE/Vultur path already shipped:
1. **DNA:** write `shared/personas/frugivoro.md` (§6). Ships into the runner image
   automatically (`COPY shared/personas/`).
2. **Registry:** add a `Persona` entry in `shared/personas/registry.py`
   (`persona_id="frugivoro"`, `token_env="FRUGIVORO_DISCORD_TOKEN"`, `bot_user_id`,
   `tts_voice`, `aliases=[]`, `gateway_enabled=False` until the Discord app + token
   exist — the same cutover gate used for ALICE). Insult auto-suppresses via the
   registry; the LLM shadow-router `_VALID_TARGETS` mirror gets `"frugivoro"`
   (lockstep test guards it).
3. **Corpus (the erudition):** clone Vultur's film-critic RAG pattern — a
   `shared/corpus/vegan_gastronomy.md` frame *(nunca existió con ese nombre: el
   header vivo es `shared/corpus/headers/frugivoro.md`)* + RAG over the **public** source subset
   (§5) in `deep_memory_chunks` under a shared namespace (e.g. `__corpus_vegan__`),
   per `project_film_critic_corpus`. This is what makes it erudite vs a thin prompt.
4. **Discord identity:** create the bot app → token → invite → set `bot_user_id` +
   `FRUGIVORO_DISCORD_TOKEN` (secret in `~/.secrets` + Container App). Flip
   `gateway_enabled=True` to go live (the gateway spins it up; it's mention-gated,
   shares the persona-runner Claude brain via `persona_id`).
5. **Benchmark loop:** run §1–§3 against Frugívoro (automated, our own bot) and the
   competitor (manual, output-only, low-volume). Iterate the DNA + corpus on the gaps.

## The decision that's the owner's
- Whether Frugívoro joins the gateway now or stays gated until the corpus is built.
- Model: Claude sibling on the persona-runner (default, like Vultur) vs a different
  brain — recommend Claude sibling (canonical, zero new infra).

## Status / next step

### Actualización 2026-08-06 (auditoría del backlog — verificado en repo)

De los 4 "pendientes para ACTIVARLO" del bloque de 2026-07-05, **3 están
verificados en el repo y el 4º (haber CORRIDO la ingesta contra el Postgres de
prod) no se pudo verificar desde esta auditoría** — el commit v4.24.4 la da por
corrida, pero eso es narrativa de commit, no un conteo de filas. El texto de
abajo quedó fósil y se conserva sólo como historia:

- **Namespace vivo**: `shared/personas/registry.py` → la entrada `frugivoro`
  lleva `corpus_namespace="__corpus_vegan__"` (comentario propio: *"el 'later
  hardening step' por fin (2026-07-16)"*).
- **Ingesta**: el script per-persona genérico existe (`scripts/ingest_corpus.py`,
  generalización del `ingest_film_corpus.py` borrado) y v4.24.0 (`d6b1297`,
  *"cada persona con su corpus — RAG generalizado"*) cableó la consulta del
  corpus en el turno de CUALQUIER persona.
- **Fuentes**: `data/corpus/frugivoro/` con MANIFEST versionado (Williams 1883
  dominio público + 2 reviews PMC CC-BY); v4.24.4 (`3dabf55`) añadió soporte
  `.xml` JATS *"frugívoro recupera sus 2 reviews"*.
- **Contenido propio**: `khimeras_shared/corpus/vegan_gastronomy.md` creció con
  frutas/IG-GL/tofu (`ed9ba53`, `8a3115a`, `19baad6`).
- **Sin verificar desde aquí**: el conteo real de chunks de `__corpus_vegan__` en
  el Postgres de prod (requiere `POSTGRES_URL` + regla de firewall para esta IP;
  no se corrió en esta auditoría). El MANIFEST de frugívoro, a diferencia del de
  Vultur, no anota el número de chunks vivos.

**Lo único vivo del item**: el benchmark ético §1–§3 (matriz de evaluación,
prompts, scoring pairwise vs el GPT competidor) — cero artefactos en el repo.
Y el volcado de conocimiento vivencial de Bernard respaldado con literatura.

### Historia — estado de 2026-07-05 (fósil, ya superado)
- **LIVE**: DNA `shared/personas/frugivoro.md`, registry entry (`gateway_enabled=True`,
  bot_user_id `1521273256236023989`, aliases frugi/frugívoro), respondiendo en
  #general; hard vegan identity endurecida en v4.21.115.
- **Corpus INICIADO (2026-07-05)**: `khimeras_shared/corpus/vegan_gastronomy.md`
  CREADO (hoy borrado — `6ba7a61`; ver arriba) — primer ladrillo con la entrada "Fruta, fructosa e índice glucémico — el
  fruit-first calibrado" (fructosa entera vs añadida, IG por persona, sesgo por
  corticoide/prednisona, fruta en autoinmune/lupus), cada afirmación respaldada con
  literatura científica per el método. **Pendiente para ACTIVARLO** (que Frugi lo
  consulte en vivo): (1) namespace `__corpus_vegan__` (módulo tipo
  `film_references.py`), (2) script de ingesta (clonar `scripts/ingest_film_corpus.py`
  → `ingest_vegan_corpus.py`), (3) correr la ingesta a `deep_memory_chunks`, (4)
  cablear Frugi para consultar el corpus vegano en sus turnos (como Vultur con el
  film corpus). Ese pipeline RAG es el siguiente slice de ingeniería. + benchmark
  ético (§1-§5). Relacionado: [[rename-frugi-to-fruggy]].

## Método destilado de Freelee — la visión del corpus (Bernard, 2026-07-05)
Lo COPIABLE de Freelee the Banana Girl NO es su venta de influencer — es su MÉTODO,
y ese método define a Frugi:
- **Fruit-first explorer**: la fruta es la base y el punto de partida; desde ahí se
  explora TODO el veganismo (técnica, fermentos, gastronomía, nutrición clínica),
  pero SIEMPRE anclado en lo fruit-based. Frugi razona desde la fruta hacia afuera,
  no desde la mímica de carne.
- **Respaldo científico obligatorio**: cada afirmación se ancla en literatura
  científica. Esa es "la receta" de Freelee (respaldarse) — y es exactamente lo que
  separa a Frugi (erudito, verificable) de Freelee (influencer que vende su resultado).

El corpus `__corpus_vegan__` se siembra con el **conocimiento vivencial de Bernard**
sobre frutas, fructosa y trucos de años — PERO cada claim de ese conocimiento se
RESPALDA con fuente científica antes de entrar al corpus (no anécdota suelta). Ese
respaldo es la mitad del trabajo, no un adorno.

Next slice: sesión de volcado donde Bernard comparte su conocimiento → Claude lo
estructura Y lo respalda con literatura → un documento nuevo en
`data/corpus/frugivoro/` (registrado en su `MANIFEST.md`) → ingesta a
`deep_memory_chunks` namespace `__corpus_vegan__` con `scripts/ingest_corpus.py`.
*(Hasta el 2026-09-25 este párrafo apuntaba a `khimeras_shared/corpus/vegan_gastronomy.md`
y a `scripts/ingest_film_corpus.py`; los dos están borrados — el primero en
`6ba7a61`, recuperable con `git show 798ba77:khimeras_shared/corpus/vegan_gastronomy.md`.)* Owner-fork: si el método fruit-first también
se endurece en el DNA (`shared/personas/frugivoro.md`) o vive solo en el corpus.
