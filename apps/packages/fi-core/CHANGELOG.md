# Changelog

All notable changes to `fi-core` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Policy:
- **PATCH**: backwards-compatible bug fixes; no public-API change.
- **MINOR**: backwards-compatible additions; new protocols, new extra, new MCP tool.
- **MAJOR**: breaking changes to Protocols, function signatures, or removed extras.

Pre-1.0 (`0.x.y`): no backwards-compat shims required. Stability promise applies at 1.0.0.

## [0.32.0] — 2026-09-10

Publica el eje de recuperación que ya vivía en `main` desde el 2026-09-09
(`22693292`) y que ningún tag alcanzó: `fi-core-v0.30.0` y `fi-core-v0.31.0`
salieron sin él, así que el consumidor —que instala el PAQUETE, no el repo—
seguía sin poder leer el otro lado de la escalera.

### Added — `PSYCHIATRY.recovery_signals`: el corpus aprende a bajar la escalera

Los 145 turnos que vivían en `stability` sin una sola señal de recuperación no
eran estabilidad: eran que nadie estaba mirando el otro lado. Cuatro grupos con
peso 3 contra umbral 4, así que ninguna señal prende sola: autorreporte, algo ya
hecho, integración, y el cierre de conversación en −3. Las promesas a futuro no
suman: una promesa es lo más fácil de decir para que te dejen en paz y nada de lo
que pase después es verificable. El cierre resta porque *"ya estoy bien, ya no
quiero hablar de eso"* da exactamente cero — esa persona no mejora, se está
cerrando, y es la que más se parece a alguien que mejora.

### Added — `silenced_by`: un contexto puede apagar un eje ENTERO

Distinto de una exclusión, que corta un span y deja al resto puntuar. En
sustancias el eje de recuperación se apaga completo, ni para bien ni para mal:
ahí no hay intervención, hay contención. Un eje silenciado nunca es un cero
pelón — `ScoredSignals.silenced` dice qué lo apagó, porque un cero por silencio y
un cero por ausencia de señal significan cosas opuestas para quien lee el log.
El eje lleva dos patrones de sustancias, el clínico y el hablado: el que ya
existía está escrito para FACTS ("alcoholismo", "consumo problemático") y no
reconoce ninguna de las formas en que una persona lo dice en un chat.

### Fixed — `WeightedSignals.score` materializa su entrada

Ahora se lee dos veces; un generador habría llegado vacío a la segunda pasada y
todo eje con silenciador habría puntuado cero en silencio.

## [0.31.0] — 2026-09-09

One defect and one dead feature, with one cause: the RAG store had two write
paths. `RagStore.ingest` replaced a document's chunks; `StoreBackedRetriever.ingest`
appended through `store.add` and applied the only contextualizer in the code base,
which no production face ever constructed. Now there is one path — the retriever
embeds and writes, `RagStore` calls it — so the fix and the feature arrive together.

### Fixed — re-ingesting a corrected document through `StoreBackedRetriever` leaves no stale chunks (one write path with `RagStore`)

`ingest("...el lunes en la sala azul.", source_ref="aviso.md")` followed by
`ingest("...el martes en la sala roja.", source_ref="aviso.md")` left BOTH
sentences retrievable (backlog `b3-fi-core-retriever-reingest-stale`, reproduced
on HDF5). `store.add` has no document concept, so the store's idempotency key —
`(namespace, source_ref, text)` — treats an edited text as a new chunk, and the
obvious patch (`delete_chunks_by_document` first) deleted zero rows because
`add`ed chunks belong to no document.

- On a `DocumentChunkStore`, **`source_ref` IS the document id**:
  `StoreBackedRetriever.ingest` now runs `get_document` → `delete_chunks_by_document`
  + `update_document(content=text)` (attributes kept) or `create_document`, then
  `save_chunks(document_id=source_ref, ...)` — the sequence `RagStore.ingest`
  already ran. A search after the correction returns only the corrected chunk;
  `get_document` shows the new content with `chunk_count == 1`.
- **`StoreBackedRetriever.replace_document(namespace, document_id, content,
  chunks, attributes=None)`** is that sequence as a method; **`RagStore.ingest`
  calls it** (its quota, `NothingToIndex` and `metadata=None`-keeps-attributes
  semantics are unchanged and pinned in `tests/test_rag_reingest_replaces.py`).
- A plain `ChunkStore` (add/query only) keeps the `add` path, and the docstring
  now says plainly that it cannot replace a `source_ref`'s chunks. Blank text, or
  text that chunks to nothing, still returns 0 without touching the store.
- Migration note: chunks the HDF5 store wrote through `add` live under a
  synthesized `_auto_<source_ref>` document; a re-ingest under `source_ref`
  writes to `source_ref` and does not remove them. Delete `_auto_*` documents
  once, or re-ingest through `RagStore`, to converge an existing corpus.

### Added — Contextual Retrieval reachable: `RagStore.from_components(contextualizer=...)`

`fi_core.rag.contextual` was unreachable from both production faces:
`from_components` hard-wired `StoreBackedRetriever(contextualizer=None)` and
`RagStore.ingest` embedded chunks itself, bypassing the retriever.

- **`StoreBackedRetriever.embed_chunks(pieces, *, document, source_ref,
  source_type="document", created_at=None) -> list[ChunkWithEmbedding]`** is the
  one embedding step: with a contextualizer set it embeds
  `"<context>\n\n<chunk>"` and returns the plain chunk for storage, so the
  citation stays verbatim. `RagStore.ingest` embeds through it.
- **`RagStore.from_components(..., contextualizer=)`** passes it into the
  retriever. `from_env` is unchanged: fi-core is LLM-agnostic and a
  `Contextualizer` needs the consumer's model call
  (`CallableContextualizer(call=...)`), so there is no env var that could build one.

## [0.30.0] — 2026-09-08

Three additions with one origin: discord-bot #54 (Alex's decisions for the
auditable band verdict, PR #68) shipped as the canary what og118 and AIRE will
need the day they log a verdict about a real person. Each is the framework
half of something the consumer had to write for itself.

### Changed — `GravityScore.reasons` are typed, never prose with the phrase inside

`reasons` was `tuple[str, ...]` of `symptom 'me quiero morir' → gravity 9` /
`comorbidity 'abuso' (+0.5)`. Right for FLOW.md's clinician reading a screen;
wrong for a log kept for years — the first real `crisis_band_classified` event
(persona-gateway rev 201) carried `"comorbidity 'abuso' (+0.5)"` verbatim, and
a grave turn would have carried the vocabulary phrase. The consumer could not
fix it without parsing prose.

- **`UrgencyReason(kind, key, weight, term)`**, frozen. `kind` ∈ `symptom` /
  `critical_pattern` / `comorbidity` / `age` / `pregnancy`; `key` names the
  vocabulary or rule that fired (`critical_symptoms`, `high_symptoms`,
  `medium_symptoms`, `unlisted`, `critical_patterns`, a `high_risk_conditions`
  entry, `over_65` / `under_1`, `pregnant`); `weight` is the contribution.
  Those three are what a log keeps. `term` — the normalized symptom or the
  matched pattern — exists for `render()` and is `repr=False`, so a serializer
  that falls back to `repr` (structlog's JSON renderer) never leaks a person's
  words by accident.
- **`UrgencyReason.render()`** returns the pre-0.30 string exactly;
  **`GravityScore.explain()`** returns all of them. The MCP `classify_urgency`
  tool still answers prose (`explain()`), as does fi-runner's `triage_guard`
  metadata.
- **Migration** (pre-1.0, no shim): a caller that read `score.reasons` as
  strings reads `score.explain()`; a caller that logs them logs
  `(r.kind, r.key, r.weight)` and stops logging phrases. discord-bot #54 is the
  first: `audit.py` logs `key`/`weight`, and the closing receipt is a KQL row
  with no vocabulary phrase in it.

### Added — `ClinicalDomain.assess()` → `ClinicalVerdict`: one call, one verdict, one explanation

A consumer that wanted the band AND the reason made two readings of the same
message with two engines — `urgency_classifier().classify(...)` for the band,
`acute_signals.matched(...)` for the explanation — and stapled them together
hoping they agreed (discord-bot's `matched_acute_groups`: *"lectura PARALELA…
si algún día divergen, el que manda es el de `crisis_band`"*). They diverged
once (0.29.1).

- **`assess(message, history=())`** runs the vocabulary match, both weighted
  axes and the classifier over the SAME text and returns
  `ClinicalVerdict(score, hits, acute, chronic, conditions)`. The group names
  in `acute.matched` / `chronic.matched` are, by construction, the ones behind
  the band; `denied` and `excluded` — which the consumer never logged because
  it would have cost a third reading — travel free (Alex's #55 H2 "señal
  débil que vale la pena registrar algún día"). `acute` / `chronic` are `None`
  on a domain without that axis (`CARDIOLOGY`).
- **`ClinicalDomain.chronic_conditions`** — chronic group name →
  `high_risk_conditions` entry — read off `SignalGroup.category`, where the
  groups already declared it. It equals discord-bot's `_GROUP_TO_CONDITION`
  verbatim (pinned in `tests/test_domain_assess.py`); the four groups with no
  counterpart score the axis and never reach the band, which is why the map is
  the domain's and not a consumer's dict. **`conditions_for(groups)`** applies it.
- `history` feeds the chronic axis and, through the map, the classifier's
  `medical_history`; a condition the message itself names is reported in
  `hits.high_risk_conditions` and does not add gravity (parity with the
  canary's `crisis_band`: the message is now, the history is the record).
- discord-bot's `crisis_band` + `matched_acute_groups` + `history_conditions` +
  `_GROUP_TO_CONDITION` collapse to this call.

### Added — `fi_core.audit`: a pseudonym that groups without identifying, and an event that carries its hash

discord-bot #68 wrote `pseudonymous_user` and `_emit` in
`khimeras_shared/audit.py`; neither is about Discord. Promoted, without
structlog and without reading the environment (the consumer owns its logger,
its key lookup and its fail-safe):

- **`pseudonym(subject, *, key, period, digest_chars=16)`** — HMAC-SHA256 with
  the period in front (`2026-09:df06…`); **`None` without a key, never a bare
  hash** (Discord ids and patient folios are small enumerable spaces; a keyless
  sha256 is reversible by anyone holding the member list). The key rotates by
  period, so a leak opens a month, not a life. Byte-compatible with the canary:
  September's codes stay comparable after the switch. The test a bare sha256
  cannot pass (two keys → two codes) is ported and mandatory.
- **`audit_period(now=None)`** — the UTC month; an aware local time is
  converted first.
- **`audited(event, **fields)`** — `fields` + `event` + `audit_hash =
  sha256_payload(...)` over both, so an `absent` row cannot be relabeled a
  verdict without moving the hash. Spreads into a structlog call:
  `log.info(**audited("crisis_band_classified", band=...))`.
- **`sha256_payload` moved here from `fi_core.cognitive.events`**, which now
  imports it; `fi_core.cognitive.sha256_payload` still resolves to the same
  function.

## [0.29.1] — 2026-09-07

### Fixed — history never fires the CRITICAL override; both layers read one negation the same way

Both found by the discord-bot session while pinning 0.29.0 (their
`test_crisis_band_observacion.py`).

- **`UrgencyClassifier.critical_pattern` scans the symptoms only.** It used to
  join `symptoms + medical_history`, so any history condition containing a
  critical pattern — `"intento de suicidio previo"`, and since 0.29.0
  `"exposición a intento de suicidio"` — forced `critical_override=True` on
  every turn of that person, message irrelevant:
  `crisis_band("hoy comí rico y salí a caminar", history=[intento previo])` →
  **CRITICAL 10**. ER semantics ported from FLOW.md; in a chat it meant every
  person with a self-harm-history fact was CRITICAL on "hoy comí rico", which
  is the single strongest reason the band could never be enabled. History
  keeps its +0.5 comorbidity modifier. Cardiology too: a past
  `"myocardial infarction 2019"` no longer overrides `"fever"`.
- **Local negation reads the clitic BEFORE the word**, where Spanish puts it.
  `"no me quiero suicidar, es broma"`: `match()` denied the vocabulary phrase
  `"me quiero suicidar"` (it starts right after the "no") while the acute
  regex, matching `"suicidar"` clitic + verb after the "no", still fired
  `explicit_ideation`. Same sentence, two verdicts. `_LOCAL_NEGATION_RE` is now
  cue → optional clitic → optional word; both layers deny.

No API change.

## [0.29.0] — 2026-09-07

### Added — Alex's H1/H2 for `PSYCHIATRY` (discord-bot #55; fi #461)

Clinical decisions Alex took on 2026-09-04/05, now executable. Every row is
pinned in `tests/test_psychiatry_h1_h2.py`.

- **`preparatory_acts`** on the acute axis at the highest weight (4): means
  secured ("tengo las pastillas listas", "compré una cuerda / soga / pistola",
  "llevo semanas guardando pastillas"), farewell written ("escribí mi carta de
  despedida", "ya me despedí de todos", "gracias por todo, ya no te preocupes
  por mí"), place reached ("estoy en el puente / la azotea / las vías"),
  possessions given away ("regalé mis cosas", "le voy a dar mi perro a mi
  hermana"), decision taken ("ya decidí cómo lo voy a hacer"), and the English
  "i have a plan and the pills ready". Tight substrings of the same acts join
  `PSYCH_CRITICAL_SYMPTOMS` / `PSYCH_CRITICAL_PATTERNS`, so the band is
  CRITICAL too — all fifteen scored LOW before. Alex: *"esto es lo que la banda
  CRITICAL necesita para significar algo"*.
- **`farewell_hint`**, weight 0: "ya no voy a estar el lunes" is reported in
  `matched` and never crosses alone. "ya arreglé mis papeles" is deliberately out.
- **Two chronic exposure groups**, same weight (2, proposed like the other
  four, hers to validate), outside `recent_grief` (PLOS Med 2020,
  doi 10.1371/journal.pmed.1003074): `exposicion_intento` ("mi hermana intentó
  suicidarse") and `exposicion_consumado` ("mi compañera se suicidó"). Their
  categories join `PSYCH_HIGH_RISK_CONDITIONS` so a consumer can map them.
  The defect they fix: both sentences scored **CRITICAL for the writer** and
  fired `self_harm_history`; now they score their own group and nothing else.
  "mi paciente intentó suicidarse" is untouched — the clinician's 3rd person.
- **Exclusions** — `SignalGroup`s whose span is cut before anything reads a
  crisis into it, reported as `excluded` on `VocabularyHits` and
  `ScoredSignals`: `modismo` ("me quiero morir de la risa", "me muero de
  hambre"), `tema_no_propio` ("vi un documental sobre el suicidio"),
  `desahogo_laboral` ("ya no puedo más con este proyecto"), and the two
  exposure groups. Declared once (`PSYCH_EXCLUSIONS`) and honored by
  `ClinicalDomain.match`, `UrgencyClassifier` (new `exclusions` field, wired by
  `urgency_classifier()`) and `WeightedSignals` (new `exclusions` field; a
  group that is also an exclusion scores itself on the span).
- **Local negation reaches the weighted axes.** `ScoredSignals.denied` lists
  groups whose every match sat right after a local cue: "no me quiero morir,
  solo estoy muy cansado" no longer crosses the acute axis and reports
  `denied=('explicit_ideation',)` — Alex's "señal débil". `fi_core.cognitive.urgency.strip_exclusions`
  and the `NamedPattern` protocol are the primitives.

## [0.28.0] — 2026-09-07

### Fixed — `PSYCHIATRY` learns "sin esperanza" and the first-person proclítico

From discord-bot #64 (Alex, measured against 0.27.0) and what surfaced while
closing it.

- **"sin esperanza" and "no tengo esperanza"** join `PSYCH_HIGH_SYMPTOMS` (gravity
  7, the tier of `"desesperanza"`). The clinical noun only fired on itself, so
  `"me siento sin esperanza"` — the form a person writes in a chat — scored LOW.
  The `_negation_shaped_terms` docstring had cited `"sin esperanza"` as a shielded
  phrase since 0.26.1 while the entry did not exist; now it does.
- **First-person proclítico crisis phrasing** joins `PSYCH_CRITICAL_SYMPTOMS` and
  `PSYCH_CRITICAL_PATTERNS`: `me quiero matar / ahorcar / suicidar / quitar la vida`
  and `me voy a matar / ahorcar / suicidar / quitar la vida`. The 3rd-person
  proclítico (`se quiere matar`) had been listed since the t15 eval case, the
  1st-person never was, so the most common way a person phrases a crisis in a
  chat scored LOW. `me quiero morir` already fired via `quiero morir`.

### Changed — negation is two-tier, by register; a chat "sin" no longer eats the sentence

Alex asked why `"sin"` negated and `"no"` did not. Accident of a cue list written
for clinical notes, and a lethal one: `"sin"` had clause scope, so
`"estoy sin dormir y me quiero matar"`, `"llevo días sin comer y quiero quitarme la
vida"` and `"sin ganas de nada, tengo un plan suicida"` all scored **LOW** (measured
by the discord-bot session against 0.27.x). Now:

1. **Clause cues** are the clinician's register only (`niega`, `no presenta`,
   `no tiene`, `no refiere`, `descarta`, `ausencia de`, `denies`, `no history of`…):
   they announce a denied list and strip to the sentence end, as before.
2. **Local cues** are what a person writes — `sin`, `no`, `nunca`, `jamás`, `ni`,
   `without`, `not`, `never` — and negate only the vocabulary term right after
   them (at most one word plus a clitic in between, never across a comma).
   `"no me quiero morir"`, `"no tengo ideación suicida"` and `"sin ideación
   suicida ni plan"` are negated; `"no sé, me quiero morir"`, `"no sé si me quiero
   morir"` and the three sentences above are positive. A term spelled with a cue
   (`"no quiero vivir"`, `"sin esperanza"`) is matched whole and never negates
   itself. The same rule runs inside `UrgencyClassifier`, so a symptom string and
   free text are read identically.

Measured before → after: the three lethal sentences LOW → **CRITICAL**;
`"no me quiero morir, solo estoy muy cansado"` CRITICAL → LOW + denied;
`"no tengo ideación suicida"` HIGH → LOW + denied. Every existing negation test
still passes, including the t13 clinical list. The real fix remains a negation
parser (free-intelligence #171).

### Added — `VocabularyHits.denied`, `scan_terms`

- `ClinicalDomain.match` now reports **`denied`**: entries that appeared only
  under a local negation. Not a hit (excluded from `bool(hits)`), but a
  consumer can log `"sigue hablando de morirse"` as a weak signal instead of
  losing it — Alex's ask for `"no me quiero morir, solo estoy muy cansado"`.
- `fi_core.cognitive.urgency.scan_terms(text, vocab, protected) -> (found, denied)`
  is the primitive; `find_terms` is its `found` half, unchanged.

## [0.27.0] — 2026-09-03

### Added — `ClinicalDomain.match(text)`: from what a person wrote to what the classifier scores

The vocabularies carry accents; a chat user, an ASR transcript or a hurried
note usually do not. 0.26.1 taught the classifier to fold what it RECEIVES,
but a consumer that finds the vocabulary inside free text by hand still
matched against the raw frozensets — 22 of PSYCHIATRY's 130 entries carry a
diacritic and none has a plain twin, so `"ando con ideacion suicida"` found
nothing and the (fixed) classifier never got a symptom (#458, measured by
discord-bot for its #53).

- `ClinicalDomain.match(text) -> VocabularyHits` folds both sides with the
  classifier's own `_fold`, strips negated clauses with the same shielded
  phrases, and returns entries in vocabulary spelling — `symptoms` (all three
  tiers, ready for `PatientContext.symptoms`), `critical_patterns` and
  `high_risk_conditions` reported separately so a consumer can see why a
  message will override or add gravity. `niega ideación suicida` finds
  nothing; `mejor sin mi` finds `mejor sin mí`.
- `fi_core.cognitive.urgency.find_terms(text, vocab, protected)` is the
  underlying primitive, public for domains built outside fi-core.
- `VocabularyHits` is exported from `fi_core.cognitive`.

Duplicating the lists with plain-spelled twins was the rejected alternative:
two spellings per entry to keep in sync by hand.

## [0.26.1] — 2026-09-02

### Fixed — the PSYCHIATRY vocabulary could not see two kinds of its own phrases

Both found by a consumer (discord-bot, issue #53) composing `UrgencyClassifier`
with `PSYCHIATRY` and measuring real phrases instead of trusting the table.

- **A symptom spelled with a negation cue was eaten before matching.** `sin` is
  a denial cue (`sin ideación suicida`), so `_strip_negations` removed
  `mejor sin mí` — a phrase that IS in `high_symptoms` — and it scored 3 like
  noise. Vocabulary phrases that carry a cue inside them are now shielded from
  the stripper; a denial that CONTAINS such a phrase (`niega sentirse mejor sin
  mí`) is still stripped whole.
- **Accents decided the band.** The classifier lowercased but never folded
  diacritics while every entry carries them: 16 PSYCHIATRY phrases changed band
  when typed without accents, 5 of them from CRITICAL to LOW (`autolesion
  activa`, `hacerme dano`). Both sides of every match — symptoms, history,
  critical patterns, comorbidities — now go through NFKD folding. `reasons` quote
  the folded input; vocabulary terms in `reasons` keep their spelling.

`tests/test_urgency_negation_accents.py` pins both, including the sweep that
every accented vocabulary entry scores identically without its accents.

## [0.25.1] — 2026-08-27 · [0.26.0] — 2026-08-28

Shipped without their own entries; this block covers both (weighted clinical
signals landed in 0.26.0).

### Fixed — the second pass: five defects that were computed and then ignored

- **A misspelled pack name disarmed the drift detector entirely.**
  `_resolve_packs` fell back to the default only when `names` was EMPTY, never
  when every name was unrecognized — so `packs=["defualt_bilingual"]` resolved to
  ZERO patterns, `check_drift` reported `clean` on an outright identity leak, and
  `validate_and_retry_prompt` dropped the `packs_unknown` field that was the
  caller's only clue. The fallback keeps responses checked; `packs_unknown` is
  now forwarded so the typo is visible instead of merely survivable.
- **Three drift patterns barely fired.** `STAGE_DIRECTIONS[0]` was the only
  pattern in the module without `(?i)`, so `*Sighs deeply*` — the capitalised,
  sentence-initial form a model actually writes — missed while its bracket
  sibling matched. `absolutely[.!]` REQUIRED punctuation glued to the word, so
  only `"Absolutely. You're right."` fired and the over-validation tier was close
  to unreachable. And the feminine `específica` was unanchored, firing
  `clarification_dump` on ordinary prose like *"Necesito la fecha específica del
  vuelo"* — which retried the turn with an instruction not to ask a clarifying
  question, aimed at a response that had asked nothing.
- **`parse_consolidation_result` raised where its contract says it returns.** A
  judge answering ```` ```[{...}]``` ```` on one line hit
  `split("\n", 1)[1]` → `IndexError`, and `consolidate_principal` calls it with
  no `try`. `consolidate_principal` now honours its documented "never raises" for
  every stage, not just the `llm_call` that happened to have a guard: a batch
  over ten thousand principals no longer dies at the first bad fence.
- **An inconsistent merge plan was applied as a partial merge.** When a judge
  referenced an id twice, the parser pruned `merge_ids` and KEPT `new_fact`, so
  the store soft-deleted one fact, inserted the merged sentence, and left the
  pruned fact alive beside it — two contradictory facts where there had been one.
  A partial merge is not a merge; the op is dropped whole and the backfill keeps
  every id. `new_fact` is also type-checked now: a dict used to reach asyncpg as
  a TEXT parameter and raise inside the transaction.
- **`semantic_search` ignored its own `limit` on every degraded path.** With no
  embedder, or a query that would not embed, or no hits in either arm, it
  returned the principals' ENTIRE fact set from a method that promises at most
  `limit` — a context blowup arriving exactly when the embedder is down.

### Changed
- Every swallowed embedder failure now LOGS, which the `save_facts` docstring had
  claimed for as long as the module had no logging import at all. The loudest is
  the consolidation path: a merged row landing unembedded while its sources are
  soft-deleted means the merge REDUCES recall.
- `cosine_similarity` returns `0.0` and warns on a dimension mismatch instead of
  the plausible number `zip(strict=False)` used to produce from the shorter
  prefix. It does not raise: `SemanticRetriever.rank` returns `[]` on a mismatch
  and a test pins that as deliberate, so the log is what makes an embedder swap
  findable without overruling a decision someone made on purpose.


### Fixed — four ways a corpus or a memory could be destroyed in silence

- **`RagStore.ingest` deleted before it knew whether it could replace.** A
  re-ingest whose text chunked to zero pieces removed the existing chunks and
  returned `0` with no error: `chunk_count` at zero, `status` back to `pending`,
  searches empty, and the byte count — the billing base — at zero. The chunking
  is now checked FIRST and raises `NothingToIndex` (a `ValueError`, so existing
  boundaries map it) with nothing stored and nothing removed. og118 had already
  collided with this and handled the `0` at its call site with a 422 telling the
  user to re-upload, after the copy they had was gone.
- **`RagStore.ingest` erased a document's `attributes` on any re-ingest that did
  not re-pass `metadata`.** A routine content correction dropped the document out
  of every filtered query its tenant ran while leaving it visible to unfiltered
  ones. `metadata=None` now means "leave them alone"; passing a dict is still how
  a caller says "these are the attributes now".
- **`PgMemoryStore.save_facts` wrote every row as `source='auto'`,** ignoring
  `f.source`. A MANUAL fact was downgraded on the way in and the next snapshot's
  `DELETE ... WHERE source='auto'` hard-deleted it — no `deleted_at`, no retention
  window — against the invariant `protocols.py` states in writing. It also
  overwrote `updated_at`; a fact carrying its own timestamp now keeps it.
- **`PgMemoryStore.save_facts(pid, [])` wiped a principal's auto memory and
  committed.** The `DELETE` ran before the empty check, and returning from inside
  the transaction context commits it. Clearing now requires `allow_empty=True`,
  because an extractor that returned nothing is far more often a failed
  extraction than a principal with no facts.

### Fixed — a hang, a rule with a hole, and a suite that could not go green

- **`ChunkConfig` accepted a window that never advances.** `overlap >=
  chunk_size` (or `chunk_size < 2`) made `chunk_by_fixed_size` loop forever
  while appending on every pass — and both numbers arrive from an agent, since
  `chunk_document` is an MCP tool, so one call hung the stdio server and ate the
  box's memory. The config is validated at construction and refuses rather than
  clamping, so nobody silently gets a different overlap than they asked for.
- **The task_tracker's backwards-dependency rule was enforced on two write paths
  of three.** `declare_plan` checked it inline and `replan` after the fact;
  `insert_step` did not check at all, so `depends_on=[7]` on a three-step plan
  was accepted and `start_step` then raised a bare `IndexError` the MCP boundary
  does not map. `depends_on=[own_index]` was accepted too and deadlocked the plan
  forever. The rule now lives in `_build_step`, the one funnel all three pass
  through, and all three are tested.
- **The pgvector test suites ERRORED instead of skipping on any host without a
  matching Postgres.** The detector accepted any `pg_ctl` on `PATH` — including
  Homebrew `libpq`, a client-only package with no `postgres` binary — and looked
  for `vector.control` in a global share tree unrelated to the chosen install.
  It now asks `pg_config --sharedir` and requires a real server binary. The
  duplicate copy of the detector in the second test module is gone: one
  `tests/pg_probe.py`. 28 errors became 28 honest skips.

### Added
- `NothingToIndex`, exported from `fi_core.rag`, and its `nothing_to_index` /
  `invalid_chunking` error payloads on the `ingest_document` MCP tool — a tool
  reports its failure, it does not kill the server.

## [0.24.4] — 2026-05-26

Brought to anaconda.org as part of the platform-engineer release pass after the channel had drifted to **0.9.1** while the source was at 0.24.4 — gap of 15 minor versions across 9 months of internal-only work.

### Added
- Proclítico reflexive forms in `PSYCH_CRITICAL_SYMPTOMS` and `PSYCH_CRITICAL_PATTERNS` (`se quiere matar`, `se quiere ahorcar`, `va a matarse`, `intenta suicidarse`, etc.). Spanish allows splitting the reflexive pronoun from the verb; substring matching now catches both forms.
- `fi_core.cognitive.urgency._strip_negations` — regex pre-pass over the input that removes clauses scoped to a negation cue (`niega`/`descarta`/`no presenta`/`sin (?!embargo)`/`denies`/`rules out`/...). Scope: cue → next sentence terminator OR opposing conjunction (`pero`, `sin embargo`, `mas`, `aunque`). Comma is intentionally NOT a clause break.
- Cross-encoder reranker (`fi-core[rerank]`): BAAI/bge-reranker-v2-m3, Apache-2.0, multilingual.
- Long-term memory primitives (`fi-core[memory]`): `PgMemoryStore` + `FactConsolidator` (Mem0-style retention).
- `task_tracker` v2: 11 MCP tools, DAG step deps, terminal-state immutability, TTL eviction, replanning, cancellation, note-step append, `list_plans`, `PlanGuard` integration in fi-runner.

### Changed
- `PSYCH_CRITICAL_SYMPTOMS` / `PSYCH_CRITICAL_PATTERNS` expanded to include 3rd-person + infinitive crisis markers (`quitarse la vida`, `ahorcarse`, `quiere morir`, `planea suicidarse`, etc.). Closes recall regressions on eval cases t04 (1st→3rd person) and t07 (vocab gap for `ahorcarse`).
- `GENERIC_AI_DISCLOSURE_ES` adds "inteligencia artificial" / "IA" patterns (closes d04 eval trap).
- `OpenAI`/`Anthropic` vendor patterns scoped to identity-claim contexts (`made/created/built/trained by`, `I'm (from) OpenAI`, `OpenAI's assistant`) instead of bare `\bOpenAI\b` (closes d11 false-positive trap).
- `mcp>=1.27,<2` pin (RFC 8707 OAuth resource validation + StreamableHTTP idle timeout).
- `fi_core.task_tracker.mcp_server._TRACKER` alias replaced with module-level `__getattr__` (PEP 562) delegating to the live `_registry._TRACKER`. Eliminates the stale-at-import-time reference.
- `_TTLStore.values()/.items()` return `list(...)` snapshots instead of dict views (defensive against future async-lock migration).
- `__init__.py` docstring rewritten: more comprehensive sub-package map, install-extras matrix, dropped the "AURITY + Insult" mention (fi-core is contract-generic).

### Eval impact (vs baseline sha 7bc3f1cd, 38 hand-labeled cases)
- Triage F1: 0.769 → **1.000** (+0.231); recall 0.714 → 1.000.
- Antidrift F1: 0.750 → **1.000** (+0.250); multi-class accuracy 0.750 → **1.000**.

## [0.9.1 — 0.24.3]

These intermediate versions were never published to anaconda.org (the channel was stuck at 0.9.1 while `dev` advanced). Highlights of the period:

- `fi_core.rag` end-to-end: `StoreBackedRetriever` + `search_documents` MCP tool.
- `fi_core.persona.mcp_server` standalone: anti-drift detectors callable from any MCP client.
- `fi_core.cognitive` clinical state machine + urgency classifier + SOAP commit gate.
- `fi_core.task_tracker` v1 → v2 rewrite (gaps catalogued in the fi-runner-task-tracker-v2 memory).
- Multiple safety hardening passes (env whitelist, RLock removal, gather logging, conversation_store guards).

For per-commit detail, browse the git history between tags `fi-core-v0.9.1` and `fi-core-v0.24.3` (when they get created) in https://github.com/BernardUriza/free-intelligence/commits/main/apps/packages/fi-core.

## [0.8.0] — 2026-05-22

### Added
- `fi_core.cognitive` — clinical cognitive-flow primitives extracted from the
  Redux-Claude medical flow (zero-dep core; YAML preset loading via the new
  `cognitive` extra):
  - `presets` / `loader` / `types` — 7 medical prompt presets as typed `CognitivePreset`.
  - `state_machine` — the clinical consultation FSM (14 states + transition table).
  - `urgency` — gravity scoring / triage (1-10 score, modifiers, widow-maker override).
  - `extraction` — extraction iteration loop (completeness %, max 5 iterations, focus).
  - `soap` — SOAP progression (section weights, NOM-004 compliance, commit gate).
  - `events` — Redux→domain-event mapping (`EventType`, `ReduxEventAdapter`, audit hash).
- `cognitive` optional extra (`pyyaml`).

### Changed
- AURITY backend now sources its prompt presets from `fi_core.cognitive`
  (single source of truth); the duplicated YAMLs and the legacy `yaml_provider`
  were removed.

## [0.7.0] — 2026-05-19

### Added

- **`fi_core.memory`** — sixth sub-package: long-term, principal-scoped
  atomic-fact memory. Consolidates the production-validated patterns
  from discord-bot's ``insult/core/memory/repositories/facts.py`` (with
  ``user_id`` generalized to ``principal_id``). Sibling of
  ``fi_core.stores``, not extension: a fact is an atomic unit, not a
  chunk of a document, so they share design language without literal
  Protocol inheritance.

- `fi_core.memory.protocols` — runtime-checkable ``MemoryStore``
  Protocol. Five capability clusters: CRUD (``get_facts``,
  ``save_facts``, ``add_fact``), soft-delete + retention
  (``soft_delete_fact``, ``purge_soft_deleted``, ``count_live``),
  search (``semantic_search``), consolidation
  (``apply_consolidation_plan``), and lifecycle (``init_schema``,
  ``close``).

- `fi_core.memory.types` — ``Fact`` dataclass (frozen, slots),
  ``FactSource`` enum (AUTO / MANUAL / AGENT — same three-tier
  provenance that protects manually curated facts from being wiped by
  auto re-extraction), ``ConsolidationOp`` audit row, and
  ``ConsolidationReport`` rollup with ``counts_by_op()``.

- `fi_core.memory.retention` — ``RetentionPolicy`` Protocol +
  three concrete impls. ``Default90d`` ships discord-bot's
  production-tuned 90-day soft-delete window (``SOFT_DELETE_RETENTION_SECONDS``).
  ``FixedWindow`` for custom durations. ``NeverPurge`` for audit-grade
  stores where soft-delete is the terminal state.

- `fi_core.memory.stores.pgvector_memory.PgMemoryStore` — production
  Postgres + pgvector impl extracted from ``FactsRepository``.
  Self-managing asyncpg pool (mirrors ``PgVectorChunkStore`` shape, not
  discord-bot's ``BaseRepository`` + ``ConnectionManager`` separation
  which only makes sense for multi-table facades). Optional injected
  ``Embedder`` for vector-backed semantic search; falls back to
  ordered-by-recency when absent. Same codec-registration-before-pool
  pattern used in ``PgVectorChunkStore`` to avoid the asyncpg "unknown
  type: vector" pitfall. Schema: ``principal_facts`` table +
  ``fact_consolidation_log`` audit table, both with full DDL +
  indexes shipped via ``init_schema()``.

- `fi_core.memory.consolidator.FactConsolidator` — high-level
  Mem0-style orchestrator. Wraps the three primitives that already
  exist (``MemoryStore`` + ``persona.mcp_server.build_consolidation_prompt``
  + ``parse_consolidation_result``). Shape B per
  ``memory:[[mcp-shape-b-canonical]]``: server builds prompt + parser,
  caller's ``llm_call`` callable executes the LLM. Returns
  ``ConsolidationReport`` with ops + counts + duration + error
  capture; never raises. ``dry_run`` synthesizes the audit trail
  without touching the store — useful for offline eval and CLI diff
  surfaces.

### Changed

- `pyproject.toml`: new ``[memory]`` optional extra
  (``asyncpg>=0.30``, ``pgvector>=0.4`` — same deps as
  ``stores-pgvector`` but named separately so the install intent is
  explicit at the caller site). ``[all]`` and ``[dev]`` already pull
  these via ``stores-pgvector``.

- `fi_core/__init__.py`: lists the new ``fi_core.memory`` path.

- `fi_core.memory.types.ConsolidationReport`: dataclass is NOT frozen
  (the orchestrator mutates it across the consolidation lifecycle —
  appending ops, recording errors, finalizing duration). All other
  types in the module remain frozen+slots.

### Honest extraction notes

- **PgMemoryStore is a direct extraction** of discord-bot's
  ``FactsRepository`` (the source file is ~310 LOC; the fi-core impl
  is ~370 LOC after collapsing the ``ConnectionManager`` separation,
  generalizing ``user_id`` to ``principal_id``, accepting an optional
  injected ``Embedder``, and inlining the audit-log writes that
  previously crossed the ``vectors`` module boundary). SQL shape and
  the soft-delete-then-reinsert UPDATE pattern are byte-identical to
  the production schema.
- **FactConsolidator orchestration logic** is the runner half of
  discord-bot's ``memory_consolidator.py`` (cleaned of Discord
  dataclasses + telemetry-routing logic). The Shape B contract with
  ``fi_core.persona.mcp_server`` is preserved unchanged.
- **Retention windows** mirror the production constant
  ``SOFT_DELETE_RETENTION_SECONDS = 90 * 86400``.

### Coverage

- 40 new tests: 6 types + 7 retention + 13 consolidator (in-memory
  mock store) + 14 PgMemoryStore (against ephemeral PG via
  pytest-postgresql).
- Full suite: 205 passing + 3 skipped (CUDA-gated on Mac runner).
  0 regressions vs 0.6.0.

### Narrative

V2 preserved: ``fi_core.memory`` ships consolidation of code that
**already passed the production filter** in two consumers (discord-bot
Insult since v3.6.0; AURITY medical RAG since 2026-Q1). It is not new
design. The same Shape B integration with ``persona.mcp_server`` that
discord-bot already uses in production is what consumers of
``FactConsolidator`` consume here — no behavioral regression, just a
narrower contract surface.

## [0.6.0] — 2026-05-19

### Added

- **`fi_core.training`** — fifth sub-package: training pipes for
  building small LMs on top of what the production stores already
  write. All sub-modules require the new ``[training]`` extra (torch +
  tiktoken + tokenizers). The base ``fi-core`` install still does NOT
  pull these.
- `fi_core.training.protocols` — runtime-checkable Protocols
  ``DatasetReader``, ``Tokenizer``, ``GenerationModel``, ``Trainer``.
  Re-exported from ``fi_core.training`` for direct ``from fi_core.training
  import DatasetReader`` use.
- `fi_core.training.datasets.HDF5DatasetReader` and
  `fi_core.training.datasets.PgVectorDatasetReader` — stream ``Chunk``
  instances out of an ``HDF5ChunkStore`` / ``PgVectorChunkStore``
  respectively. The reader takes a constructed store (not a path or
  DSN) so the caller controls lifecycle.
- `fi_core.training.tokenizers.TiktokenTokenizer` — thin wrapper over
  OpenAI's ``tiktoken`` library. Default encoding ``cl100k_base`` (the
  GPT-4 vocab, 100,277 tokens). Use with the ``tiny_gpt_30m`` preset.
- `fi_core.training.tokenizers.BPETokenizer` — wraps HuggingFace's
  ``tokenizers`` library (fast Rust BPE trainer). Static ``train``
  classmethod for fitting a corpus-specific BPE; ``save`` / ``load``
  for persistence. Default special tokens: ``<pad>``, ``<unk>``,
  ``<bos>``, ``<eos>``. Use with the ``tiny_gpt_5m`` preset.
- `fi_core.training.models.TinyGPT` + ``GPTConfig`` — compact
  decoder-only Transformer (karpathy-style minGPT): pre-LayerNorm
  blocks, tied embedding ↔ unembedding, GELU activations, causal
  self-attention via ``F.scaled_dot_product_attention`` (PyTorch ≥2.0
  picks flash-attention automatically on supported GPUs). ``forward``
  takes optional ``targets`` and returns ``(logits, loss)``.
  ``generate`` does autoregressive sampling with temperature, top-k,
  top-p (nucleus), and repetition penalty — logic adapted from
  Robo-Poet's ``src/legacy/robo-poet-pytorch/src/generation/generate.py``.
  ``configure_optimizers`` returns AdamW with the standard
  decay / nodecay parameter split.
- `fi_core.training.models.presets` — factory functions
  ``tiny_gpt_5m`` (8K vocab, ~5M params) and ``tiny_gpt_30m``
  (cl100k_base, ~30M params). Both use 6 layers × 8 heads × 256
  hidden, 256-token context, dropout 0.1.
- `fi_core.training.trainers.PyTorchTrainer` — config-driven training
  loop. Adapted from Robo-Poet's
  ``src/legacy/robo-poet-pytorch/src/training/train.py``. Changes:
  GPU-only (fails fast with a clear ``RuntimeError`` on no CUDA — no
  CPU or MPS path), config-driven optimizer (``optimizer_cls`` +
  ``optimizer_kwargs``, default falls back to
  ``model.configure_optimizers`` if available), TensorBoard stripped
  in favor of structlog events, ``torch.amp.GradScaler('cuda')`` API.
  Features mixed precision, gradient accumulation, linear warmup →
  cosine decay LR schedule, gradient clipping, best-loss checkpoint
  tracking, early stopping.

### Changed

- `pyproject.toml`: new ``[training]`` optional extra
  (``torch>=2.0``, ``tiktoken>=0.7``, ``tokenizers>=0.20``). ``[all]``
  and ``[dev]`` updated.
- `fi_core/__init__.py`: lists the new ``fi_core.training`` path.

### Narrative

V2 preserved: training is a utility surface, NOT a closed loop. The
patterns shipped by ``fi_core.persona`` are NOT derived from any
corpus a consumer trains on with this module — they remain
human-distilled from production failure modes. ``fi_core.training``
ships the pipes (read chunks that ``fi_core.stores`` wrote, tokenize,
embed, run a small GPT loop); the closed loop, if a consumer wants
one, is their assembly.

### Honest reuse notes

- ``TinyGPT`` model code was written for fi-core (Robo-Poet referenced
  a ``models.gpt_model`` that never existed in the repo — Bernard's
  comment ``tu PyTorch existe; tu loop no`` was literal: only the
  trainer was real).
- ``PyTorchTrainer`` is a near-verbatim adaptation of Robo-Poet's
  ``GPTTrainer`` class, with the changes documented above.
- Generation sampling (temperature / top-k / top-p / repetition
  penalty) is adapted from Robo-Poet's ``TextGenerator``.
- Tokenizers are thin wrappers over ``tiktoken`` and HuggingFace
  ``tokenizers`` — no point reinventing what those libraries already
  do well.

## [0.5.1] — 2026-05-19

### Added

- `fi_core.persona.mcp_server.build_consolidation_prompt(facts, max_tokens_hint)`
  and `fi_core.persona.mcp_server.parse_consolidation_result(raw_response, facts)`
  — Shape B tools (per the canonical MCP pattern: server returns
  prompt + parser, NEVER executes LLM). Mem0-style judge consolidation
  ported verbatim from discord-bot's `insult/core/memory_consolidator.py`.
  Pairs so any consumer (insult-runner via Claude Code SDK + OAuth Max,
  AURITY's curator, fi-monitor) can run the judge call with its own
  credentials. The system prompt is byte-identical to discord-bot's
  `insult/prompts/memory_consolidator_judge.md`. Parser strips markdown
  fences, validates op shape against the input facts list, backfills
  implicit NOOPs for ids the judge omitted (never silently lose a row).
- `fi_core.persona.MCP_SERVER_NAME` and `fi_core.persona.MCP_TOOLS` —
  explicit MCP contract constants that v0.4.0 forgot to export. Lists
  all 7 tools (5 from 0.4.0 + 2 new consolidation tools). Re-exported
  from `fi_core.persona` so consumers can do
  `from fi_core.persona import MCP_SERVER_NAME, MCP_TOOLS` without
  digging into `mcp_server` internals. This closes the gap that forced
  discord-bot's `scripts/sync_capabilities.py` to AST-walk
  `mcp_server.py` as a fallback in 0.4.0.

### Notes

- 0.5.0 shipped to GitHub + anaconda.org before these two persona
  additions landed on `main`. 0.5.1 is a fast follow that bundles the
  consolidation tools + MCP contract constants into the same release
  cycle; nothing else changed (same pgvector store, same embedders).
  Downstream consumers should target `fi-core>=0.5.1` to unlock the
  consolidation pair and the explicit `MCP_TOOLS` discovery path.

## [0.5.0] — 2026-05-19

### Added

- `fi_core.stores.pgvector.PgVectorChunkStore` — second reference
  `DocumentChunkStore` implementation, backed by Postgres + pgvector.
  Designed for multi-tenant chat substrates that need concurrent writes,
  relational filters mixed with vector similarity, and transactional
  consistency. IVFFlat index (`lists=100`) by default; documented HNSW
  migration cue for >1M chunks per namespace. Codec registration is
  done via one-shot bare connection BEFORE pool construction (avoids
  the asyncpg "unknown type: vector" failure mode). 7 new tests using
  pytest-postgresql's ephemeral PG fixture.
- `fi_core.embeddings.azure_openai.AzureOpenAIEmbedder` — first
  reference `Embedder` implementation. Wraps Azure OpenAI's embeddings
  API via the openai SDK's `AsyncAzureOpenAI` client. Constructor takes
  explicit config (api_key, endpoint, deployment, api_version, dim) —
  NO env-var reading inside the package; caller's job to source
  credentials. Default `dim=1536` (text-embedding-ada-002 /
  text-embedding-3-small), parameterizable to 3072 for
  text-embedding-3-large. 14 new tests with mocked SDK calls — no
  network access in CI.
- `fi_core.embeddings.sentence_transformers.SentenceTransformersEmbedder` —
  second reference `Embedder` implementation. Loads a local
  sentence-transformers model into the host process (CPU by default;
  GPU via `device=` parameter, with auto-detect ladder
  `cuda > mps > cpu` when `device=None`). Lazy-load on first `embed()`
  call (model is NOT loaded at `__init__`). `model.encode` runs through
  `asyncio.to_thread` so it does not block the event loop. Default
  model `sentence-transformers/all-MiniLM-L6-v2` (384-dim, matches
  AURITY's fi-monitor GPU service). 8 new tests including a
  `@pytest.mark.slow` real-model load + encode test.

### Changed

- `fi_core/__init__.py` updated to list the four new sub-package paths.
- `pyproject.toml`: new optional extras `stores-pgvector` (asyncpg +
  pgvector), `embeddings-azure` (openai), `embeddings-st`
  (sentence-transformers + torch). `[all]` and `[dev]` updated to
  bundle all five extras. Default `numpy` and `mcp` upper bounds also
  formalized in `[stores-hdf5]` and `[mcp]` (matching the conda recipe).
- `[tool.pytest.ini_options]` registers a `slow` marker for the heavy
  sentence-transformers real-model test, eliminating
  PytestUnknownMarkWarning at collection.

### Honest extraction notes

- `AzureOpenAIEmbedder` was a clean extraction from discord-bot's
  `insult/core/deep_memory.py` (lines 48-129). Stripped env-var
  reading, promoted dim to a constructor arg, added eager validation.
- `SentenceTransformersEmbedder` is "inspired by" not "extracted from"
  AURITY. AURITY's `monitor_client.py` is a thin HTTP client to a
  Cloudflare-tunneled GPU service; no `MonitorClientEmbedder` class
  exists. The fi-core implementation is a clean local-process
  equivalent modeled on `fi-monitor/rag_service/main.py:71` (the
  actual SentenceTransformer instantiation point in the free-
  intelligence monorepo).
- `PgVectorChunkStore` is "inspired by" not "extracted from"
  discord-bot's `deep_memory.py`. The discord-bot module is heavily
  Discord-domain (hardcoded `user_id` column, closed CHECK constraint
  on source_type, md5-based chunk dedupe, no document concept). The
  fi-core implementation preserves the schema shape, cosine query
  pattern, and IVFFlat index choice, but drops Discord-specific
  concepts and adds the full document-lifecycle layer needed by
  the `DocumentChunkStore` Protocol.

### Coverage

- 29 new tests (14 azure + 8 sentence-transformers + 7 pgvector).
- Full suite: 124 passing in 8.87s. 0 regressions.

## [0.4.0] — 2026-05-19

### Added

- `fi_core.persona.mcp_server` — MCP (Model Context Protocol) server
  exposing the persona detectors as tools that any MCP-compatible AI
  (Claude Code, Cursor, Anthropic API with MCP enabled) can call
  directly, without depending on `fi-core` as a Python package in
  its own process.
- Five tools shipped on the server:
  - `list_packs()` — discovery of atomic + composite packs with
    severity, language, and pattern count metadata.
  - `check_drift(text, packs)` — detect persona drift with matches
    grouped by severity tier (break / soft_drift / clarification_dump).
  - `sanitize_response(text, packs)` — last-resort sentence-level
    cleanup for break-severity matches.
  - `get_reinforcement(pack_name)` — return the reinforcement string
    associated with a pack. Auto-maps `clarification_dump_*` to
    `CONTEXT_REINFORCEMENT`, everything else to `GENERIC_REINFORCEMENT`.
  - `validate_and_retry_prompt(response, system_prompt, packs)` —
    one-shot atomic loop. The killer-feature tool: validates the
    response, decides per-severity whether retry is needed, and
    returns the reinforced system prompt if so. Zero client-side
    orchestration; the AI does not need a state machine.
- Composite packs (`default_bilingual`, `all_ai_disclosure`, etc.) now
  expand to their atomic components when processed by the MCP server,
  preserving per-pattern severity tier end-to-end. A hard break inside
  `default_bilingual` is routed through the break-tier detector, not
  the soft-drift one.
- 21 new tests in `test_persona_mcp.py` covering all five tools, the
  atomic-vs-composite expansion contract, unknown-pack graceful
  fallback, severity-precedence rules, and the no-retry-on-soft-drift
  decision rule.

### Changed

- `fi-core` now ships an optional `[mcp]` extra (depends on `mcp>=1.4`).
  Install as `pip install 'fi-core[mcp]'` to enable the server.
- Anaconda conda recipe `meta.yaml` keeps `mcp` as a non-required
  dependency since the base package remains usable without it; the
  conda-forge submission will declare it as optional output.

### Install + register

```bash
pip install 'fi-core[mcp]'
claude mcp add fi-core-persona -- python -m fi_core.persona.mcp_server
```

After registration, any MCP client (Claude Code, Cursor) can invoke the
five tools directly. The killer use case is the meta-validation loop:
the AI checks its own output for persona drift via `validate_and_retry_prompt`
before sending the response to the user, and retries with the right
reinforcement automatically if drift is detected.

## [0.3.0] — 2026-05-19

### Added

- `fi_core.rag.DocumentChunkStore` Protocol — explicit interface for
  persistent chunk storage, decoupled from any specific backend.
- `fi_core.stores.hdf5.HDF5ChunkStore` — first concrete implementation
  of `DocumentChunkStore`, backed by HDF5 via `h5py`. Supports both
  async and sync APIs.
- New type module surface:
  - `ChunkWithEmbedding` — chunk text + its vector representation.
  - `DocumentMetadata` — document-level metadata associated with a
    chunk set.
  - `DocumentRecord` — combined record returned by store lookups.
- Optional install group `stores-hdf5` (pulls `h5py>=3.10`, `numpy>=1.24`).
- 34 new tests covering the HDF5 store and the protocol contract.

### Notes

- The core package remains zero-dependency. HDF5 is opt-in via
  `pip install fi-core[stores-hdf5]`.

## [0.2.0] — 2026-05-19

### Added

- `fi_core.persona` — character-integrity / anti-drift module
  extracted from the production Insult Discord bot.
- Three detector classes:
  - `BreakDetector` — hard identity leaks (retry-worthy).
  - `AntiPatternMonitor` — soft drift toward assistant tone (log only).
  - `ClarificationDumpDetector` — bot punting the task back at the
    user despite having context (retry with context cue).
- `sanitize()` — last-resort sentence-level cleanup when retries fail.
- `DetectionResult` dataclass — frozen value type with `clean`
  convenience flag and `severity` field for telemetry routing.
- 14 built-in pattern packs covering:
  - AI identity disclosure (`GENERIC_AI_DISCLOSURE_EN`, `..._ES`).
  - Assistant tone (`ASSISTANT_TONE_EN`, `..._ES`).
  - Therapy-speak (`THERAPY_SPEAK_EN`, `..._ES`).
  - Summarizing (`SUMMARIZING`).
  - Stage directions / roleplay drift (`STAGE_DIRECTIONS`).
  - Markdown formatting drift (`MARKDOWN_DRIFT`).
  - Moralizing (`MORALIZING_EN`, `..._ES`).
  - Over-validation (`OVER_VALIDATION_EN`, `..._ES`).
  - Clarification dump (`CLARIFICATION_DUMP_ES`).
- Convenience composite packs: `ALL_AI_DISCLOSURE`,
  `ALL_ASSISTANT_TONE`, `ALL_THERAPY_SPEAK`, `ALL_MORALIZING`,
  `ALL_OVER_VALIDATION`, `DEFAULT_EN`, `DEFAULT_ES`,
  `DEFAULT_BILINGUAL`.
- Reinforcement strings: `GENERIC_REINFORCEMENT`,
  `CONTEXT_REINFORCEMENT`, `IDENTITY_REINFORCEMENT_SUFFIX`.
- 31 new tests pinning the detector contracts and pack invariants
  (e.g. all packs contain only compiled `re.Pattern` objects, default
  composites equal the concatenation of their sources).

### Notes

- All persona detection is deterministic regex — zero LLM calls at
  detection time, zero embeddings, zero training data required.
- Bilingual EN+ES patterns are first-class peers, not afterthoughts.
- Persona-specific patterns stay in the consumer's codebase; the
  library only ships patterns that generalize across personas.

## [0.1.0] — 2026-05-19

### Added

- Initial release.
- `fi_core.rag` — chunking algorithm extracted verbatim from the
  AURITY `document_service` production code.
  - Three strategies: paragraph-aware, sentence-aware, fixed-size.
  - `ChunkingStrategy` enum and `ChunkConfig` dataclass.
  - `chunk_document(text, strategy, config) -> list[str]` entry point.
- `Embedder` Protocol — async `embed(text) -> list[float]` contract
  for any embedding backend (sentence-transformers, Azure OpenAI
  ada-002, etc.).
- `ChunkStore` Protocol — first-pass storage contract (later superseded
  by `DocumentChunkStore` in 0.3.0).
- `Chunk` and `RetrievedChunk` dataclasses for typed chunk values.
- 9 tests covering chunking behavior across strategies and edge cases.

### Notes

- Zero runtime dependencies. The package targets Python 3.12+.
- Intended consumers at extraction time: AURITY (on-prem medical) and
  the Insult Discord bot (Azure-native conversational).

[0.3.0]: https://github.com/BernardUriza/free-intelligence/releases/tag/fi-core-v0.3.0
[0.2.0]: https://github.com/BernardUriza/free-intelligence/releases/tag/fi-core-v0.2.0
[0.1.0]: https://github.com/BernardUriza/free-intelligence/releases/tag/fi-core-v0.1.0
