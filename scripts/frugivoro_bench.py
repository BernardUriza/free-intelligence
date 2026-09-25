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

Fidelidad (si algo se desvía, se mide otro sistema):
  - La respuesta sale de `/v1/turn` del persona-runner con `persona_id=frugivoro`,
    el mismo cliente que usa el gateway (`AgentRunnerClient`).
  - `behavioral_guidance` se arma como en el gateway: el bloque del corpus RAG
    (`build_persona_corpus_block`, namespace `__corpus_vegan__`) PRIMERO, y luego
    la guidance del guardián para un usuario SIN facts (`build_turn_guidance`).
    `--no-corpus` es el contrafactual: mide qué aporta el corpus.
  - Usuario sintético `bench-frugivoro`: sin facts, no contamina a nadie real.

Costo y efectos de una corrida real (por eso NO se corre sin autorización):
  - Un turno de Frugívoro por caso contra el runner de prod (gasto AIRE/Max) y una
    fila en `turn_jobs` por turno (el boleto durable). Con `--judge`, una llamada
    `/v1/judge` por caso; con `--competitor`, DOS más por caso (orden invertido).
  - El corpus lee Postgres (`POSTGRES_URL`) y el servicio de embeddings: sólo
    lectura.

Uso:
    python scripts/frugivoro_bench.py --dry-run          # valida la suite, arma los
                                                         # payloads, cero red, cero gasto
    python scripts/frugivoro_bench.py --dry-run --answers scratchpad/frugi_bench.json
                                                         # re-puntúa (deterministas)
                                                         # respuestas ya guardadas

    # corrida real (requiere autorización de Bernard — gasta y escribe turn_jobs):
    PERSONA_RUNNER_URL=... PERSONA_RUNNER_TOKEN=... POSTGRES_URL=... \\
        python scripts/frugivoro_bench.py --split dev --judge
    # + pairwise contra respuestas del competidor recogidas a mano:
    ... python scripts/frugivoro_bench.py --split dev --judge \\
        --competitor data/benchmarks/frugivoro/competitor_manual.json

El set `heldout` NUNCA se usa para iterar el ADN; se corre sólo para confirmar.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
SUITE_DIR = ROOT / "data" / "benchmarks" / "frugivoro"
CASES_PATH = SUITE_DIR / "cases.json"
JUDGE_ABSOLUTE_PATH = SUITE_DIR / "judge_absolute.md"
JUDGE_PAIRWISE_PATH = SUITE_DIR / "judge_pairwise.md"

PERSONA_ID = "frugivoro"
BENCH_USER_ID = "bench-frugivoro"
BENCH_CHANNEL_ID = "bench-frugivoro"
SPLITS = ("dev", "heldout")


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
    present_tiers = {c.get("tier") for c in cases}
    for tier in tiers - present_tiers:
        errors.append(f"nivel {tier!r} sin casos: la matriz tendría una columna vacía")
    splits = {c.get("split") for c in cases}
    if "heldout" not in splits:
        errors.append("no hay casos heldout: §1 exige un set contra el que nunca se itera")
    return errors


def select_cases(suite: dict[str, Any], split: str) -> list[dict[str, Any]]:
    cases = suite["cases"]
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
    return {
        "cases": len(results),
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


# ── red (sólo en corrida real) ───────────────────────────────────────────────


async def _guidance_for(prompt: str, *, with_corpus: bool) -> str | None:
    from khimeras_shared.guidance import MAX_GUIDANCE_CHARS, build_turn_guidance

    guidance = build_turn_guidance(
        current_message=prompt,
        recent_messages=None,
        user_facts=[],
        persona_id=PERSONA_ID,
        user_id=BENCH_USER_ID,
    )
    if not with_corpus:
        return guidance
    from shared.corpus.persona_corpus import build_persona_corpus_block

    block = await build_persona_corpus_block(persona_id=PERSONA_ID, query=prompt)
    if not block:
        return guidance
    if not guidance:
        return block[:MAX_GUIDANCE_CHARS]
    budget = MAX_GUIDANCE_CHARS - len(guidance) - 2
    return guidance if budget <= 0 else f"{block[:budget]}\n\n{guidance}"


async def _run_live(args, suite, cases) -> list[dict[str, Any]]:
    from khimeras_shared.runner.agent_client import AgentRunnerClient
    from khimeras_shared.runner.judge_client import RunnerJudgeClient

    url = os.environ["PERSONA_RUNNER_URL"]
    token = os.environ["PERSONA_RUNNER_TOKEN"]
    agent = AgentRunnerClient(url, token, timeout_s=600.0)
    judge = RunnerJudgeClient(url, token) if (args.judge or args.competitor) else None
    competitor = load_competitor(Path(args.competitor)) if args.competitor else {}
    abs_tpl = JUDGE_ABSOLUTE_PATH.read_text(encoding="utf-8")
    pair_tpl = JUDGE_PAIRWISE_PATH.read_text(encoding="utf-8")

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
        for n, case in enumerate(cases, 1):
            row: dict[str, Any] = {"id": case["id"], "tier": case["tier"], "split": case["split"]}
            try:
                guidance = await _guidance_for(case["prompt"], with_corpus=not args.no_corpus)
                resp = await agent.chat(
                    "",
                    [{"role": "user", "content": case["prompt"]}],
                    persona_id=PERSONA_ID,
                    user_id=BENCH_USER_ID,
                    channel_id=BENCH_CHANNEL_ID,
                    behavioral_guidance=guidance,
                )
                row["answer"] = resp.text
                row["model"] = resp.model_used
                row["deterministic"] = deterministic_checks(resp.text, case, suite)
                if args.judge:
                    row["judge"] = validate_absolute(
                        await ask_judge(render_absolute_prompt(abs_tpl, case, resp.text, suite)), case, suite
                    )
                if case["id"] in competitor:
                    other = competitor[case["id"]]
                    v1 = await ask_judge(render_pairwise_prompt(pair_tpl, case, resp.text, other, suite))
                    v2 = await ask_judge(render_pairwise_prompt(pair_tpl, case, other, resp.text, suite))
                    row["pairwise"] = pairwise_outcome(str(v1.get("winner")), str(v2.get("winner")))
            except Exception as exc:  # un caso caído no tira la corrida; queda registrado
                row["error"] = repr(exc)
            det = row.get("deterministic", {})
            print(f"[{n:2}] {case['id']:32} det={'ok' if det.get('passed') else 'FALLA'} {row.get('error', '')}")
            results.append(row)
    finally:
        if judge is not None:
            await judge.aclose()
    return results


# ── CLI ──────────────────────────────────────────────────────────────────────


def _dry_run(args, suite, cases) -> int:
    from khimeras_shared.guidance import build_turn_guidance

    abs_tpl = JUDGE_ABSOLUTE_PATH.read_text(encoding="utf-8")
    pair_tpl = JUDGE_PAIRWISE_PATH.read_text(encoding="utf-8")
    for n, case in enumerate(cases, 1):
        rendered = render_absolute_prompt(abs_tpl, case, "<respuesta>", suite)
        # La guidance del guardián es pura (sin facts, sin red): el payload real se
        # arma igual que en la corrida; sólo el bloque del corpus RAG queda fuera.
        guidance = build_turn_guidance(
            current_message=case["prompt"],
            recent_messages=None,
            user_facts=[],
            persona_id=PERSONA_ID,
            user_id=BENCH_USER_ID,
        )
        print(
            f"[{n:2}] {case['tier']:6} {case['split']:7} {case['id']:32} "
            f"guidance={len(guidance or '')} juez={len(rendered)} chars"
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
    ap.add_argument("--dry-run", action="store_true", help="valida y arma, sin red ni gasto")
    ap.add_argument("--answers", help="dry-run: re-puntúa (deterministas) un JSON de salida previo")
    ap.add_argument("--judge", action="store_true", help="puntúa cada respuesta con el juez (/v1/judge)")
    ap.add_argument("--judge-model", default=None, help="modelo del juez; vacío = default del runner")
    ap.add_argument("--competitor", help="JSON de respuestas del competidor recogidas A MANO")
    ap.add_argument("--no-corpus", action="store_true", help="contrafactual: sin el bloque RAG __corpus_vegan__")
    ap.add_argument("--out", default="scratchpad/frugivoro_bench.json")
    args = ap.parse_args(argv)

    suite = load_suite()
    errors = validate_suite(suite)
    if errors:
        for e in errors:
            print(f"suite inválida: {e}", file=sys.stderr)
        return 2
    cases = select_cases(suite, args.split)
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
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    out.with_suffix(".summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\ndetalle → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
