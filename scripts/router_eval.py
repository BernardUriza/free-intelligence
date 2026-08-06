"""Eval offline del router gpt-4.1 contra mensajes REALES de #general.

La ventana A.2.3 (scripts/router_window.sh) mide el ruteo en vivo, pero se llena
al ritmo del tráfico orgánico — a un turno por día tardaría semanas. Esto mide lo
mismo HOY: toma los mensajes que de verdad se escribieron en #general, reconstruye
el contexto EXACTO que el stage le pasa al router en prod, y llama al gpt-4.1 real.

Fidelidad (si algo de esto se desvía, el eval mide otro sistema):
  - El contexto son los 8 mensajes previos INCLUYENDO el propio, porque el stage
    corre después de `memory_store` y el mensaje ya está en la tabla.
  - Mismo formato `user_name: content[:300]`, oldest-first, que `_fetch_router_context`.
  - Mismo transporte (`DirectAzureLLMRouter`) y mismo deployment que prod.
  - **Se excluyen los mensajes dirigidos a un sibling** (mención o alias vocativo).
    `batch.py` los suprime ANTES del pipeline, así que el router jamás los ve;
    evaluarlos mediría una población que en prod no existe. El predicado se importa
    del repo (`shared.personas.addressing`), no se reimplementa aquí.

No escribe nada: es lectura de Postgres + llamadas de clasificación. NO contamina la
ventana orgánica (no pasa por Discord ni emite `llm_router_cutover_decision`).

Reproducibilidad: sin `--until`, el eval toma los mensajes más recientes, así que
mañana mide OTRO conjunto y no sirve como regresión. El set de 30 casos con el que
se cazó y corrigió el secuestro de v4.22.23 se recupera cortando el pool en
`2026-07-09T04:11:00Z` (justo después de la respuesta de Vultur al probe). Ese es
el set canónico: re-córrelo tras tocar `demux_ai/prompts/host_routing.md`.

Uso:
    POSTGRES_URL=... AZURE_OPENAI_KEY=... python scripts/router_eval.py --limit 30
    python scripts/router_eval.py --limit 30 --dry-run   # extrae y muestra, cero gasto

    # el set de regresión canónico, congelado:
    python scripts/router_eval.py --limit 30 --until 2026-07-09T04:11:00Z
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

GENERAL_CHANNEL_ID = "1489180895264116736"
ROUTER_CONTEXT_MESSAGES = 8
USD_PER_INPUT_TOKEN = 2.0 / 1_000_000
USD_PER_OUTPUT_TOKEN = 8.0 / 1_000_000


def _addressed_to_sibling(content: str) -> bool:
    from shared.personas.addressing import any_alias_is_addressee
    from shared.personas.registry import sibling_aliases, sibling_bot_user_ids

    for bot_id in sibling_bot_user_ids():
        if f"<@{bot_id}>" in content or f"<@!{bot_id}>" in content:
            return True
    return any_alias_is_addressee(sibling_aliases(), content)


def _context_block(rows: list[dict], upto: int) -> str | None:
    window = rows[max(0, upto - ROUTER_CONTEXT_MESSAGES + 1) : upto + 1]
    lines = [
        f"{r.get('user_name', '?')}: {str(r.get('content', ''))[:300]}"
        for r in window
        if str(r.get("content", "")).strip()
    ]
    return "\n".join(lines) if lines else None


async def _load_messages(pg_url: str, channel_id: str, pool: int, until_ts: float | None = None) -> list[dict]:
    import asyncpg

    conn = await asyncpg.connect(pg_url)
    try:
        rows = await conn.fetch(
            "SELECT user_id, user_name, role, content, timestamp FROM messages "
            "WHERE channel_id = $1 AND timestamp <= $2 ORDER BY timestamp DESC LIMIT $3",
            channel_id,
            until_ts if until_ts is not None else 1e18,
            pool,
        )
    finally:
        await conn.close()
    return [dict(r) for r in reversed(rows)]


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30, help="casos a evaluar")
    ap.add_argument("--pool", type=int, default=400, help="mensajes a traer para muestrear")
    ap.add_argument("--channel", default=GENERAL_CHANNEL_ID)
    ap.add_argument("--dry-run", action="store_true", help="no llama a gpt-4.1")
    ap.add_argument(
        "--until",
        default=None,
        help="corta el pool en este instante ISO-8601 (ej. 2026-07-09T04:11:00Z). "
        "Sin él, el eval toma los mensajes MÁS RECIENTES y evalúa un conjunto distinto cada día.",
    )
    ap.add_argument(
        "--no-context",
        action="store_true",
        help="rutea SIN el bloque de conversación reciente — el contrafactual que mide qué "
        "aporta el contexto. Es lo que corre HOY en prod: el host no tiene POSTGRES_URL y "
        "host_loop.tick nunca pasa `context`, así que RULE 1 del prompt (continuación, la de "
        "máxima prioridad) es inalcanzable. Corre el mismo set con y sin esta flag y compara.",
    )
    ap.add_argument("--out", default="scratchpad/router_eval.json")
    args = ap.parse_args()

    pg_url = os.environ.get("POSTGRES_URL")
    if not pg_url:
        print("falta POSTGRES_URL", file=sys.stderr)
        return 2

    until_ts = None
    if args.until:
        from datetime import datetime

        until_ts = datetime.fromisoformat(args.until.replace("Z", "+00:00")).timestamp()
        print(f"ventana congelada hasta {args.until} (epoch {until_ts:.0f})")

    rows = await _load_messages(pg_url, args.channel, args.pool, until_ts)
    user_msgs = [(i, r) for i, r in enumerate(rows) if r["role"] == "user" and str(r["content"]).strip()]
    cases = [(i, r) for i, r in user_msgs if not _addressed_to_sibling(str(r["content"]))]
    skipped = len(user_msgs) - len(cases)
    cases = cases[-args.limit :]
    print(
        f"mensajes en el pool: {len(rows)} · de usuario: {len(user_msgs)} · "
        f"excluidos por ir dirigidos a un sibling: {skipped} · evaluables: {len(cases)}\n"
    )

    if args.dry_run:
        for i, (_idx, r) in enumerate(cases, 1):
            print(f"[{i:2}] {r['user_name']}: {str(r['content'])[:110]}")
        print("\ndry-run: cero llamadas, cero gasto.")
        return 0

    from demux_ai.llm_shadow_router import DirectAzureLLMRouter

    router = DirectAzureLLMRouter()
    results, in_tok, out_tok = [], 0, 0

    for n, (idx, r) in enumerate(cases, 1):
        text = str(r["content"])
        context = None if args.no_context else _context_block(rows, idx)
        try:
            d = await router.route(text, context)
        except Exception as exc:  # una falla no debe tirar el eval entero
            print(f"[{n:2}] ERROR {type(exc).__name__}: {exc}")
            results.append({"text": text, "error": repr(exc)})
            continue
        in_tok += d.input_tokens
        out_tok += d.output_tokens
        results.append(
            {
                "user": r["user_name"],
                "text": text,
                "target": d.target,
                "reason": d.reason,
                "input_tokens": d.input_tokens,
            }
        )
        flag = "→ SIBLING" if d.target != "insult" else ""
        print(f"[{n:2}] {d.target:10} {flag:10} | {r['user_name']}: {text[:80]}")

    ok = [r for r in results if "target" in r]
    to_sibling = [r for r in ok if r["target"] != "insult"]
    usd = in_tok * USD_PER_INPUT_TOKEN + out_tok * USD_PER_OUTPUT_TOKEN

    print(f"\n{'=' * 60}")
    print(f"decisiones ok      : {len(ok)}/{len(cases)}")
    print(f"ruteadas a sibling : {len(to_sibling)} ({len(to_sibling) / max(1, len(ok)):.1%})")
    for r in to_sibling:
        print(f"   [{r['target']}] {r['user']}: {r['text'][:70]}")
    print(f"tokens             : {in_tok} in / {out_tok} out")
    print(f"costo              : ${usd:.4f}")
    print("\nEl reparto NO es el veredicto. Cada ruteo a sibling se revisa a mano:")
    print("¿el mensaje pedía a esa persona, o solo mencionaba su tema?")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\ndetalle → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
