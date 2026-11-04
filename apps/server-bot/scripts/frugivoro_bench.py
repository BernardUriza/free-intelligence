"""Benchmark de Frugívoro — el §1–§3 de `.claude/backlog/frugivoro-persona.md`.

Mide a Frugívoro contra una matriz fija (dimensiones × niveles de dificultad),
con tres capas de puntuación, de la más barata a la más cara:

  1. **Deterministas** (cero gasto): cada caso trae grupos de patrones que la
     respuesta DEBE tocar (`expect_any`) y patrones prohibidos (`forbid`, más el
     `forbid_all` de la suite: fuga de identidad). Es un piso, no un veredicto.
  2. **Juez absoluto** (G-Eval): Likert 1–5 anclado por dimensión + los 9
     marcadores de erudición, con el prompt en `data/benchmarks/frugivoro/
     judge_absolute.md` (contenido, no código).
  3. **Pairwise contra el competidor**: A/B anónimo con el orden INVERTIDO en una
     segunda pasada; si las dos pasadas no coinciden, es empate (mata el sesgo de
     posición). Agrega a un win-rate.

**La frontera ética (Bernard, no negociable):** las respuestas del GPT competidor
entran SÓLO como un archivo JSON escrito a mano (`--competitor`), recogidas
preguntando en su interfaz pública, en bajo volumen, y cada entrada declara
`"collected_by": "manual"`. Este script NO habla con el competidor, no extrae su
prompt ni sus archivos, y rechaza un archivo que no declare recolección manual.

Superficie (2026-10-03): Discord está APAGADO desde el 2026-09-27, así que el
único camino vivo es el del runner que usa og118. Cada turno sale como PROBE:
  - El cuerpo lo arma `scripts/probe_turn.py::build_probe_payload` — la única
    fábrica de identidad de prueba: `origin="probe"`, principal
    `probe-frugivoro-bench` (el runner rechaza con 422 un probe que no empiece por
    `probe-`), y un canal `probe-<fecha>-fb-<corrida>-<brazo>-<caso>` PROPIO por
    caso, para que ningún caso lea como "conversación reciente" a otro. Nunca
    bajo el user_id de una persona real. Las filas quedan etiquetadas
    `messages.origin='probe'` y nunca se minan facts de ellas.
  - Viaja por boleto (`POST /v1/turn/jobs` + poll corto), nunca en una request
    que el ingress corte a los 240 s.

Los dos brazos — lo ÚNICO que cambia entre ellos es el bloque del corpus:
  - `corpus` (default): `pipeline="runner"`. El runner corre `run_turn` — guardián,
    corpus `__corpus_vegan__`, framing — exactamente como para og118.
  - `--no-corpus`: `pipeline="caller"`. El harness arma lo mismo que `run_turn`
    para un canal vacío y un principal sin facts (mismo `compose_user_text`, misma
    guidance del guardián) y NO le pega corpus. Es el contrafactual: un canal
    nuevo no tiene historia ni memoria relevante, así que el resto del turno es
    idéntico.

¿Llegó el corpus a la respuesta? (`corpus_trace`) — con `POSTGRES_URL` +
`AZURE_OPENAI_*` el harness corre, de sólo lectura, la MISMA recuperación que
`run_turn` (`query_corpus` con la pregunta cruda, mismo piso de similitud) y anota
qué pasajes pasaron. Luego busca su huella en la respuesta: la procedencia
nombrada (`corpus_sources` de la suite) y términos/cifras distintivos de los
pasajes que no venían en la pregunta. Veredicto por caso: `no_retrieval` (nada
clareó el piso), `not_injected` (clareó el piso pero el bloque salió vacío — el
corpus no llegó al turno), `cited` (nombra la procedencia de un pasaje
recuperado — señal fuerte), `echoed` (repite términos/cifras de los pasajes —
débil), `ungrounded`, o `unknown` (sin
credenciales para reproducir la recuperación). El veredicto que importa es la
DIFERENCIA contra el brazo `--no-corpus` sobre los mismos casos.

Costo y efectos de una corrida real (la completa espera autorización de Bernard):
  - Un turno de Frugívoro por caso contra el runner de prod (gasto AIRE/Max,
    despierta el runner si está en cero), una fila en `turn_jobs` por turno, y en
    el brazo `corpus` dos filas `messages` etiquetadas `origin='probe'`. Con
    `--judge`, una llamada `/v1/judge` por caso; con `--competitor`, DOS más.
  - `corpus_trace` lee Postgres y el servicio de embeddings: sólo lectura.

Uso:
    python scripts/frugivoro_bench.py --dry-run          # valida la suite y arma los
                                                         # payloads: cero red, cero gasto
    python scripts/frugivoro_bench.py --dry-run --answers scratchpad/frugi_bench.json
                                                         # re-puntúa respuestas guardadas

    # humo (1 caso, los dos brazos = 2 turnos):
    PERSONA_RUNNER_URL=... PERSONA_RUNNER_TOKEN=... POSTGRES_URL=... AZURE_OPENAI_ENDPOINT=... \\
    AZURE_OPENAI_KEY=... python scripts/frugivoro_bench.py --case corpus-embarazo --out scratchpad/fb_corpus.json
    ... python scripts/frugivoro_bench.py --case corpus-embarazo --no-corpus --out scratchpad/fb_nocorpus.json

    # corrida completa (autorización de Bernard): los dos brazos, el mismo día
    ... python scripts/frugivoro_bench.py --split dev --judge --out scratchpad/fb_dev_corpus.json
    ... python scripts/frugivoro_bench.py --split dev --judge --no-corpus --out scratchpad/fb_dev_nocorpus.json
    # + pairwise contra respuestas del competidor recogidas a mano:
    ... --competitor data/benchmarks/frugivoro/competitor_manual.json

El set `heldout` NUNCA se usa para iterar el ADN; se corre sólo para confirmar.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from probe_turn import PROBE_PREFIX, build_probe_payload  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUITE_DIR = ROOT / "data" / "benchmarks" / "frugivoro"
CASES_PATH = SUITE_DIR / "cases.json"
JUDGE_ABSOLUTE_PATH = SUITE_DIR / "judge_absolute.md"
JUDGE_PAIRWISE_PATH = SUITE_DIR / "judge_pairwise.md"

PERSONA_ID = "frugivoro"
CORPUS_NAMESPACE = "__corpus_vegan__"
# El principal de prueba. Nunca un id real: el runner rechaza (422) un probe
# cuyo user_id no empiece por `probe-`, y este nombre lo deja grepeable.
PROBE_ID = "frugivoro-bench"
BENCH_USER_ID = f"{PROBE_PREFIX}{PROBE_ID}"
BENCH_SURFACE = "bench"
SPLITS = ("dev", "heldout")
ARMS = ("corpus", "no-corpus")

# Las costuras que cruzan el ingress de ACA (240 s): el alta y cada poll quedan
# muy por debajo; el presupuesto del TURNO es el del gateway (600 s).
SUBMIT_READ_TIMEOUT_S = 200.0
POLL_WAIT_S = 45
POLL_READ_TIMEOUT_S = 60.0
TURN_BUDGET_S = 600.0

# Huella del corpus: cuántos términos/cifras de los pasajes recuperados (ausentes
# de la pregunta) tienen que reaparecer en la respuesta para leerla como apoyada
# en ellos cuando no nombra la procedencia. Heurística: el número que manda es la
# diferencia contra el brazo --no-corpus, no este umbral.
GROUNDING_MIN_SHARED_TERMS = 3


# ── suite ────────────────────────────────────────────────────────────────────


def load_suite(path: Path = CASES_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_suite(suite: dict[str, Any]) -> list[str]:
    """Todo lo que haría mentir al benchmark, como lista de errores (vacía = sana)."""
    errors: list[str] = []
    dims = set(suite.get("dimensions", {}))
    tiers = set(suite.get("tiers", []))
    cases = suite.get("cases", [])
    if not cases:
        return ["la suite no trae casos"]
    for pattern in suite.get("forbid_all", []):
        try:
            re.compile(pattern)
        except re.error as exc:
            errors.append(f"forbid_all: regex inválido {pattern!r}: {exc}")
    seen: set[str] = set()
    for case in cases:
        cid = case.get("id", "<sin id>")
        if cid in seen:
            errors.append(f"{cid}: id duplicado")
        seen.add(cid)
        if not str(case.get("prompt", "")).strip():
            errors.append(f"{cid}: prompt vacío")
        if case.get("tier") not in tiers:
            errors.append(f"{cid}: tier desconocido {case.get('tier')!r}")
        if case.get("split") not in SPLITS:
            errors.append(f"{cid}: split desconocido {case.get('split')!r}")
        case_dims = case.get("dimensions", [])
        if not case_dims:
            errors.append(f"{cid}: sin dimensiones")
        for d in case_dims:
            if d not in dims:
                errors.append(f"{cid}: dimensión desconocida {d!r}")
        groups = case.get("expect_any", [])
        if not groups:
            errors.append(f"{cid}: sin expect_any (un caso sin piso determinista no mide nada barato)")
        for group in groups:
            if not group:
                errors.append(f"{cid}: grupo expect_any vacío (pasaría siempre)")
            for pattern in group:
                if pattern != normalize(pattern):
                    errors.append(f"{cid}: patrón {pattern!r} con acentos/mayúsculas nunca matchea el texto normalizado")
                try:
                    re.compile(pattern)
                except re.error as exc:
                    errors.append(f"{cid}: regex inválido {pattern!r}: {exc}")
        for pattern in case.get("forbid", []):
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(f"{cid}: regex inválido {pattern!r}: {exc}")
    for label, patterns in suite.get("corpus_sources", {}).items():
        if not patterns:
            errors.append(f"corpus_sources[{label}]: sin patrones (una cita nunca se reconocería)")
        for pattern in patterns:
            if pattern != normalize(pattern):
                errors.append(f"corpus_sources[{label}]: patrón {pattern!r} con acentos/mayúsculas nunca matchea")
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(f"corpus_sources[{label}]: regex inválido {pattern!r}: {exc}")
    if any(c.get("corpus_expected") for c in cases) and not suite.get("corpus_sources"):
        errors.append("hay casos corpus_expected pero la suite no declara corpus_sources")
    present_tiers = {c.get("tier") for c in cases}
    for tier in tiers - present_tiers:
        errors.append(f"nivel {tier!r} sin casos: la matriz tendría una columna vacía")
    splits = {c.get("split") for c in cases}
    if "heldout" not in splits:
        errors.append("no hay casos heldout: §1 exige un set contra el que nunca se itera")
    return errors


def select_cases(suite: dict[str, Any], split: str, ids: list[str] | None = None) -> list[dict[str, Any]]:
    """Los casos de un split, o exactamente los `ids` pedidos (para un humo de 1–3 turnos)."""
    cases = suite["cases"]
    if ids:
        by_id = {c["id"]: c for c in cases}
        unknown = [i for i in ids if i not in by_id]
        if unknown:
            raise ValueError(f"casos desconocidos: {unknown}")
        return [by_id[i] for i in ids]
    return cases if split == "all" else [c for c in cases if c["split"] == split]


# ── capa 1: deterministas ────────────────────────────────────────────────────


def normalize(text: str) -> str:
    """Minúsculas y sin acentos — los patrones de la suite se escriben así."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def deterministic_checks(answer: str, case: dict[str, Any], suite: dict[str, Any]) -> dict[str, Any]:
    norm = normalize(answer)
    failures: list[str] = []
    min_chars = case.get("min_chars", suite.get("min_chars_default", 0))
    if len(answer.strip()) < min_chars:
        failures.append(f"respuesta de {len(answer.strip())} chars < mínimo {min_chars}")
    for group in case.get("expect_any", []):
        if not any(re.search(p, norm) for p in group):
            failures.append(f"falta alguno de {group}")
    for pattern in [*suite.get("forbid_all", []), *case.get("forbid", [])]:
        if re.search(pattern, norm):
            failures.append(f"aparece lo prohibido {pattern!r}")
    return {"passed": not failures, "failures": failures}


# ── huella del corpus ────────────────────────────────────────────────────────

_WORD = re.compile(r"[a-z0-9][a-z0-9-]*")


def _distinctive_terms(text: str) -> set[str]:
    """Cifras (2+ dígitos) y palabras largas, truncadas a 8 letras.

    El truncado es un stemming pobre que cruza idiomas donde importa: los pasajes
    de las revisiones PMC están en inglés y la persona contesta en español
    (`cardiometabolic` ↔ `cardiometabólico` comparten `cardiome`).
    """
    out: set[str] = set()
    for tok in _WORD.findall(normalize(text)):
        if sum(ch.isdigit() for ch in tok) >= 2:
            out.add(tok)
        elif len(tok) >= 9:
            out.add(tok[:8])
    return out


def corpus_grounding(
    answer: str,
    retrieval: dict[str, Any] | None,
    prompt: str,
    suite: dict[str, Any],
) -> dict[str, Any]:
    """¿Dejaron huella en la respuesta los pasajes que el corpus le dio al turno?

    `retrieval` = lo que devuelve `retrieve_corpus` (`cleared` / `injected`, cada
    uno `[{label, similarity, text}]`), o None si no se pudo reproducir.
    """
    if retrieval is None:
        return {"verdict": "unknown"}
    if not retrieval["cleared"]:
        return {"verdict": "no_retrieval"}
    hits = retrieval["injected"]
    if not hits:
        # Clareó el piso y aun así el bloque salió vacío: el corpus NO llegó al
        # turno. No es "la persona lo ignoró" — es el read-path que lo tiró.
        return {"verdict": "not_injected", "cleared": sorted({h["label"] for h in retrieval["cleared"]})}
    norm, pnorm = normalize(answer), normalize(prompt)
    labels = sorted({h["label"] for h in hits})
    sources = suite.get("corpus_sources", {})
    cited = [
        label
        for label in labels
        if any(re.search(p, norm) and not re.search(p, pnorm) for p in sources.get(label, []))
    ]
    passage_terms = set().union(*(_distinctive_terms(h.get("text", "")) for h in hits))
    shared = sorted((passage_terms & _distinctive_terms(answer)) - _distinctive_terms(prompt))
    # `cited` es la señal fuerte: la cabecera del corpus le ORDENA a la persona
    # decir de dónde sale lo que usó. `echoed` es débil — vocabulario del tema
    # puede coincidir sin el corpus — y sólo significa algo contra el brazo
    # --no-corpus sobre el mismo caso.
    if cited:
        verdict = "cited"
    elif len(shared) >= GROUNDING_MIN_SHARED_TERMS:
        verdict = "echoed"
    else:
        verdict = "ungrounded"
    return {
        "verdict": verdict,
        "retrieved": labels,
        "cited": cited,
        "shared_terms": shared[:20],
        "shared_count": len(shared),
    }


# ── capa 2/3: prompts del juez (contenido en .md) ────────────────────────────


def _fill(template: str, values: dict[str, str]) -> str:
    # replace y no str.format: la plantilla trae el JSON de salida con llaves literales.
    for key, value in values.items():
        template = template.replace("{" + key + "}", value)
    return template


def _dimension_lines(case: dict[str, Any], suite: dict[str, Any]) -> str:
    return "\n".join(f"- `{d}` — {suite['dimensions'][d]}" for d in case["dimensions"])


def render_absolute_prompt(template: str, case: dict[str, Any], answer: str, suite: dict[str, Any]) -> str:
    markers = "\n".join(f"- `{mid}` — {text}" for mid, text in suite["markers"].items())
    return _fill(
        template,
        {
            "prompt": case["prompt"],
            "answer": answer,
            "dimensions": _dimension_lines(case, suite),
            "markers": markers,
        },
    )


def render_pairwise_prompt(template: str, case: dict[str, Any], answer_a: str, answer_b: str, suite) -> str:
    return _fill(
        template,
        {
            "prompt": case["prompt"],
            "answer_a": answer_a,
            "answer_b": answer_b,
            "dimensions": _dimension_lines(case, suite),
        },
    )


def parse_judge_json(text: str) -> dict[str, Any]:
    """El primer objeto JSON del texto del juez. Levanta ValueError si no hay."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"el juez no devolvió JSON: {text[:120]!r}")
    return json.loads(text[start : end + 1])


def validate_absolute(verdict: dict[str, Any], case: dict[str, Any], suite: dict[str, Any]) -> dict[str, Any]:
    """Se queda sólo con lo que el caso mide; un score fuera de 1–5 es un error, no un dato."""
    scores = verdict.get("scores", {})
    clean: dict[str, int] = {}
    for d in case["dimensions"]:
        value = scores.get(d)
        if not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"{case['id']}: score inválido para {d}: {value!r}")
        clean[d] = value
    markers = [m for m in verdict.get("markers", []) if m in suite["markers"]]
    return {"scores": clean, "markers": markers, "rationale": str(verdict.get("rationale", ""))}


def pairwise_outcome(frugi_as_a: str, frugi_as_b: str) -> str:
    """Combina las dos pasadas (Frugívoro como A, luego como B) en un resultado.

    Sólo cuenta como victoria lo que sobrevive al cambio de orden; si las pasadas
    se contradicen, el juez estaba votando por la POSICIÓN y es empate.
    """
    first = {"A": "frugivoro", "B": "competitor"}.get(frugi_as_a, "tie")
    second = {"A": "competitor", "B": "frugivoro"}.get(frugi_as_b, "tie")
    return first if first == second else "tie"


# ── competidor: sólo recolección manual ──────────────────────────────────────


def load_competitor(path: Path) -> dict[str, str]:
    """`{case_id: {"text": ..., "collected_by": "manual", "collected_at": ...}}`.

    Rechaza cualquier entrada que no declare recolección manual: la frontera ética
    del item (output-only, manual, bajo volumen) vive aquí, no en la buena fe.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for cid, entry in raw.items():
        if not isinstance(entry, dict) or entry.get("collected_by") != "manual":
            raise ValueError(f"{cid}: toda respuesta del competidor debe declarar collected_by='manual'")
        text = str(entry.get("text", "")).strip()
        if not text:
            raise ValueError(f"{cid}: respuesta del competidor vacía")
        out[cid] = text
    return out


# ── agregado ─────────────────────────────────────────────────────────────────


def summarize(results: list[dict[str, Any]], suite: dict[str, Any]) -> dict[str, Any]:
    """Matriz dimensión × nivel (media del juez), piso determinista y win-rate."""
    det = [r for r in results if "deterministic" in r]
    matrix: dict[str, dict[str, list[int]]] = {}
    marker_hits: dict[str, int] = dict.fromkeys(suite["markers"], 0)
    judged = 0
    for r in results:
        judge = r.get("judge")
        if not judge:
            continue
        judged += 1
        for dim, score in judge["scores"].items():
            matrix.setdefault(dim, {}).setdefault(r["tier"], []).append(score)
        for m in judge["markers"]:
            marker_hits[m] += 1
    pair = [r["pairwise"] for r in results if r.get("pairwise")]
    wins = sum(1 for p in pair if p == "frugivoro")
    losses = sum(1 for p in pair if p == "competitor")
    corpus: dict[str, int] = {}
    for r in results:
        verdict = (r.get("corpus_trace") or {}).get("verdict")
        if verdict:
            corpus[verdict] = corpus.get(verdict, 0) + 1
    return {
        "cases": len(results),
        "errors": sum(1 for r in results if r.get("error")),
        "corpus_trace": corpus,
        "deterministic_passed": sum(1 for r in det if r["deterministic"]["passed"]),
        "deterministic_total": len(det),
        "judged": judged,
        "matrix": {
            dim: {tier: round(sum(v) / len(v), 2) for tier, v in by_tier.items()} for dim, by_tier in matrix.items()
        },
        "marker_hits": marker_hits,
        "pairwise": {
            "n": len(pair),
            "wins": wins,
            "losses": losses,
            "ties": len(pair) - wins - losses,
            # empate = medio punto, la convención de Chatbot Arena para win-rate.
            "win_rate": round((wins + 0.5 * (len(pair) - wins - losses)) / len(pair), 3) if pair else None,
        },
    }


# ── el turno: probe por el wire del runner ───────────────────────────────────


def guardian_guidance(prompt: str) -> str | None:
    """La guidance del guardián para un principal SIN facts — la que `run_turn` arma."""
    from persona_core.guidance import build_turn_guidance

    return build_turn_guidance(
        current_message=prompt,
        recent_messages=None,
        user_facts=[],
        persona_id=PERSONA_ID,
        user_id=BENCH_USER_ID,
    )


def build_turn_payload(case: dict[str, Any], *, arm: str, run_id: str, today: str | None = None) -> dict[str, Any]:
    """El cuerpo de `/v1/turn/jobs` de un caso, siempre como probe.

    `corpus` → `pipeline="runner"` con la pregunta cruda: el runner corre
    `run_turn` (guardián + corpus + framing) como para og118.
    `no-corpus` → `pipeline="caller"`: lo mismo que `run_turn` arma para un canal
    vacío y un principal sin facts, menos el bloque del corpus.
    """
    if arm not in ARMS:
        raise ValueError(f"brazo desconocido {arm!r}")
    payload = build_probe_payload(
        case["prompt"],
        persona=PERSONA_ID,
        # Un canal por caso y por corrida: run_turn lee la historia reciente del
        # canal, y un caso no debe ver a otro como "lo que se acaba de decir".
        slug=f"fb-{run_id}-{arm}-{case['id']}",
        probe_id=PROBE_ID,
        surface=BENCH_SURFACE,
        pipeline="runner" if arm == "corpus" else "caller",
        today=today,
    )
    payload["job_id"] = f"fb-{run_id}-{uuid.uuid4().hex[:16]}"
    if arm == "no-corpus":
        from persona_core.turn.framing import compose_user_text

        payload["user_text"] = compose_user_text(case["prompt"], [{"role": "user", "content": case["prompt"]}])
        guidance = guardian_guidance(case["prompt"])
        if guidance:
            payload["behavioral_guidance"] = guidance
    return payload


async def run_probe_turn(http, url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Alta del boleto + poll corto hasta que el turno termine. Devuelve el TurnResponse.

    El alta es idempotente por `job_id`, así que un ReadTimeout del arranque en
    frío se reintenta con el MISMO id (nunca un turno doble).
    """
    import httpx

    headers = {"Authorization": f"Bearer {token}"}
    deadline = time.monotonic() + TURN_BUDGET_S
    while True:
        try:
            accepted = await http.post(
                f"{url}/v1/turn/jobs",
                json=payload,
                headers=headers,
                timeout=httpx.Timeout(SUBMIT_READ_TIMEOUT_S, connect=10.0),
            )
            break
        except (httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
            if time.monotonic() >= deadline:
                raise
            await asyncio.sleep(2.0)
    if accepted.status_code != 202:
        raise RuntimeError(f"alta rechazada http={accepted.status_code}: {accepted.text[:300]}")
    job_id = accepted.json()["job_id"]
    while time.monotonic() < deadline:
        try:
            got = await http.get(
                f"{url}/v1/turn/jobs/{job_id}",
                params={"wait_s": POLL_WAIT_S},
                headers=headers,
                timeout=httpx.Timeout(POLL_READ_TIMEOUT_S, connect=10.0),
            )
        except (httpx.ReadTimeout, httpx.ConnectError, httpx.ConnectTimeout):
            continue  # se cayó el poll, no el turno
        if got.status_code != 200:
            raise RuntimeError(f"poll http={got.status_code}: {got.text[:300]}")
        body = got.json()
        if body.get("status") == "done":
            return body["response"]
    raise TimeoutError(f"turno {job_id} sin terminar tras {TURN_BUDGET_S:.0f}s")


async def retrieve_corpus(prompt: str) -> dict[str, Any] | None:
    """Reproduce, de sólo lectura, lo que el corpus le da al turno de `run_turn`.

    Dos medidas, porque divergen: `cleared` = los pasajes que pasan el piso de
    similitud; `injected` = los que de verdad entran al bloque, calculado con la
    MISMA función que el runner (`build_persona_corpus_block`). Medido 2026-10-03:
    un pasaje que clarea el piso pero excede `_REF_MAX_CHARS` hace que el bloque
    salga vacío SIN log — por eso no basta con mirar la similitud.

    None = no se pudo reproducir (sin credenciales o falla): "no sé", nunca "no hubo".
    """
    if not os.environ.get("POSTGRES_URL") or not os.environ.get("AZURE_OPENAI_KEY"):
        return None
    from persona_core.corpus.references import _REF_MIN_SIMILARITY, _REF_TOP_K, cite_label, query_corpus
    from shared.corpus.persona_corpus import build_persona_corpus_block

    hits = await query_corpus(prompt.strip(), namespace=CORPUS_NAMESPACE, top_k=_REF_TOP_K)
    if not hits:
        # query_corpus devuelve [] también cuando falla el embed o Postgres: con
        # credenciales puestas, un corpus de cientos de chunks vacío es "no sé".
        return None
    cleared = [
        {"label": cite_label(h.get("source_ref")), "similarity": round(h["similarity"], 3), "text": h["chunk_text"]}
        for h in hits
        if h["similarity"] >= _REF_MIN_SIMILARITY
    ]
    block = await build_persona_corpus_block(persona_id=PERSONA_ID, query=prompt) if cleared else None
    injected = [h for h in cleared if block and h["text"].strip() in block]
    return {"cleared": cleared, "injected": injected, "block_chars": len(block or "")}


async def _run_live(args, suite, cases) -> list[dict[str, Any]]:
    import httpx

    from persona_core.runner.judge_client import RunnerJudgeClient

    url = os.environ["PERSONA_RUNNER_URL"].rstrip("/")
    token = os.environ["PERSONA_RUNNER_TOKEN"]
    arm = "no-corpus" if args.no_corpus else "corpus"
    run_id = args.run_id or uuid.uuid4().hex[:6]
    judge = RunnerJudgeClient(url, token) if (args.judge or args.competitor) else None
    competitor = load_competitor(Path(args.competitor)) if args.competitor else {}
    abs_tpl = JUDGE_ABSOLUTE_PATH.read_text(encoding="utf-8")
    pair_tpl = JUDGE_PAIRWISE_PATH.read_text(encoding="utf-8")
    print(f"brazo={arm} corrida={run_id} principal={BENCH_USER_ID}\n")

    async def ask_judge(prompt: str) -> dict[str, Any]:
        resp = await judge.utility_call(
            "Evalúas respuestas culinarias. Devuelves sólo JSON.",
            [{"role": "user", "content": prompt}],
            model=args.judge_model,
            max_tokens=800,
        )
        return parse_judge_json(resp.text)

    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient() as http:
            for n, case in enumerate(cases, 1):
                row: dict[str, Any] = {"id": case["id"], "tier": case["tier"], "split": case["split"], "arm": arm}
                try:
                    payload = build_turn_payload(case, arm=arm, run_id=run_id)
                    row["channel_id"] = payload["channel_id"]
                    started = time.monotonic()
                    resp = await run_probe_turn(http, url, token, payload)
                    row["elapsed_s"] = round(time.monotonic() - started, 1)
                    answer = resp.get("text", "")
                    row["answer"] = answer
                    row["model"] = resp.get("model")
                    row["output_tokens"] = resp.get("output_tokens")
                    row["deterministic"] = deterministic_checks(answer, case, suite)
                    retrieval = await retrieve_corpus(case["prompt"])
                    if retrieval is not None:
                        row["retrieved"] = {
                            "cleared": [{"label": h["label"], "similarity": h["similarity"]} for h in retrieval["cleared"]],
                            "injected": len(retrieval["injected"]),
                            "block_chars": retrieval["block_chars"],
                        }
                    row["corpus_trace"] = corpus_grounding(answer, retrieval, case["prompt"], suite)
                    if args.judge:
                        row["judge"] = validate_absolute(
                            await ask_judge(render_absolute_prompt(abs_tpl, case, answer, suite)), case, suite
                        )
                    if case["id"] in competitor:
                        other = competitor[case["id"]]
                        v1 = await ask_judge(render_pairwise_prompt(pair_tpl, case, answer, other, suite))
                        v2 = await ask_judge(render_pairwise_prompt(pair_tpl, case, other, answer, suite))
                        row["pairwise"] = pairwise_outcome(str(v1.get("winner")), str(v2.get("winner")))
                except Exception as exc:  # un caso caído no tira la corrida; queda registrado
                    row["error"] = f"{type(exc).__name__}: {exc}"
                det = row.get("deterministic", {})
                trace = (row.get("corpus_trace") or {}).get("verdict", "-")
                print(
                    f"[{n:2}] {case['id']:32} det={'ok' if det.get('passed') else 'FALLA'} "
                    f"corpus={trace} {row.get('elapsed_s', '')}s {row.get('error', '')}"
                )
                results.append(row)
    finally:
        if judge is not None:
            await judge.aclose()
    return results


# ── CLI ──────────────────────────────────────────────────────────────────────


def _dry_run(args, suite, cases) -> int:
    abs_tpl = JUDGE_ABSOLUTE_PATH.read_text(encoding="utf-8")
    pair_tpl = JUDGE_PAIRWISE_PATH.read_text(encoding="utf-8")
    arm = "no-corpus" if args.no_corpus else "corpus"
    for n, case in enumerate(cases, 1):
        rendered = render_absolute_prompt(abs_tpl, case, "<respuesta>", suite)
        # El payload real, armado igual que en la corrida (sin red): el brazo
        # corpus deja el corpus al runner; el no-corpus lleva la guidance aquí.
        payload = build_turn_payload(case, arm=arm, run_id="dryrun")
        print(
            f"[{n:2}] {case['tier']:6} {case['split']:7} {case['id']:32} "
            f"pipeline={payload['pipeline']} principal={payload['user_id']} "
            f"guidance={len(payload.get('behavioral_guidance') or '')} juez={len(rendered)} chars"
        )
        render_pairwise_prompt(pair_tpl, case, "<a>", "<b>", suite)
    if args.competitor:
        competitor = load_competitor(Path(args.competitor))
        print(f"\ncompetidor (manual): {len(competitor)} respuestas válidas")
    if args.answers:
        saved = {r["id"]: r for r in json.loads(Path(args.answers).read_text(encoding="utf-8"))}
        results = []
        for case in cases:
            if case["id"] in saved and saved[case["id"]].get("answer"):
                results.append(
                    {
                        "id": case["id"],
                        "tier": case["tier"],
                        "deterministic": deterministic_checks(saved[case["id"]]["answer"], case, suite),
                    }
                )
        s = summarize(results, suite)
        print(f"\nre-puntuado determinista: {s['deterministic_passed']}/{s['deterministic_total']}")
        for r in results:
            if not r["deterministic"]["passed"]:
                print(f"   {r['id']}: {r['deterministic']['failures']}")
    print("\ndry-run: cero llamadas al runner, cero gasto.")
    return 0


async def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--split", choices=[*SPLITS, "all"], default="dev")
    ap.add_argument("--case", action="append", dest="cases", help="sólo este caso (repetible) — para un humo")
    ap.add_argument("--dry-run", action="store_true", help="valida y arma, sin red ni gasto")
    ap.add_argument("--answers", help="dry-run: re-puntúa (deterministas) un JSON de salida previo")
    ap.add_argument("--judge", action="store_true", help="puntúa cada respuesta con el juez (/v1/judge)")
    ap.add_argument("--judge-model", default=None, help="modelo del juez; vacío = default del runner")
    ap.add_argument("--competitor", help="JSON de respuestas del competidor recogidas A MANO")
    ap.add_argument("--no-corpus", action="store_true", help="contrafactual: el mismo turno sin el bloque del corpus")
    ap.add_argument("--run-id", default=None, help="sufijo de los canales probe (default: aleatorio)")
    ap.add_argument("--out", default="scratchpad/frugivoro_bench.json")
    args = ap.parse_args(argv)

    suite = load_suite()
    errors = validate_suite(suite)
    if errors:
        for e in errors:
            print(f"suite inválida: {e}", file=sys.stderr)
        return 2
    try:
        cases = select_cases(suite, args.split, args.cases)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"suite v{suite['version']}: {len(suite['cases'])} casos · split={args.split} → {len(cases)}\n")

    if args.dry_run:
        return _dry_run(args, suite, cases)

    missing = [v for v in ("PERSONA_RUNNER_URL", "PERSONA_RUNNER_TOKEN") if not os.environ.get(v)]
    if missing:
        print(f"falta {', '.join(missing)} (o usa --dry-run)", file=sys.stderr)
        return 2

    results = await _run_live(args, suite, cases)
    summary = summarize(results, suite)
    print(f"\n{'=' * 60}\n{json.dumps(summary, ensure_ascii=False, indent=2)}")
    print("\nEl piso determinista NO es el veredicto: revisa a mano los fallos y cada pairwise.")
    print("corpus_trace sólo significa algo contra el brazo --no-corpus de los mismos casos, el mismo día.")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    out.with_suffix(".summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\ndetalle → {out}")
    return 0 if not summary["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
