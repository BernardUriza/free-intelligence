"""Salud del ruteo del host, con veredicto — no un volcado de logs.

Existe porque el 2026-08-06 el router llevaba tres semanas mandando el 97.6% de
los turnos a insult (331/339 en 30 días) y NADA estaba rojo: cada turno logueaba
`llm_insult`, un clean match, que se lee como salud. El defecto sólo se encontró
leyendo el hilo a mano. Un sesgo así no se detecta mirando turnos sueltos — hay
que agregar y comparar contra un umbral.

Cada bloque contesta una pregunta que un turno individual NO puede contestar:

  SESGO        ¿el cerebro está eligiendo, o contesta siempre lo mismo?
  CONTEXTO     ¿los turnos llevan conversación, o rutean a ciegas?
  CONTINUIDAD  ¿cuántos turnos cambian de persona, y cuántos de esos cambios
               ocurrieron SIN contexto (el secuestro de continuaciones)?
  ESFUERZO     ¿el effort que el prompt pide llega, y varía?
  MUDEZ        ¿las ramas de fallo se dispararon? Un cero aquí es bueno, PERO
               ver la sección "ramas que no pueden sonar".

Uso:
    python scripts/router_health.py            # últimos 7 días
    python scripts/router_health.py --days 30
    python scripts/router_health.py --days 1 --channel 1489180895264116736

Requiere `az login` (toma el token de Log Analytics con el az CLI). El workspace
es el de insult-rg; ver memoria `reference_azure_log_analytics`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request

WORKSPACE = "14ebd989-62d2-4207-b099-f6e13256fd72"
HOST_APP = "khimeras-host"

# Umbrales. El de fallback (5%) es la práctica de industria para routers en prod;
# el de sesgo (90%) es el mismo que este repo ya usa para el anti-drift de presets
# ("flag si 90%+ de las clasificaciones son DEFAULT_ABRASIVE") — la misma vacuna,
# aplicada al router en vez de al clasificador de presets.
BIAS_ALERT = 0.90
CONTEXT_ALERT = 0.95
DEFAULT_TARGET = "insult"


def _token() -> str:
    out = subprocess.run(  # noqa: S603
        ["az", "account", "get-access-token", "--resource", "https://api.loganalytics.io", "--query", "accessToken", "-o", "tsv"],  # noqa: S607, E501
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0 or not out.stdout.strip():
        print("no hay token de Azure — corre `az login` primero", file=sys.stderr)
        raise SystemExit(2)
    return out.stdout.strip()


def _query(kql: str, token: str) -> list[list]:
    req = urllib.request.Request(  # noqa: S310
        f"https://api.loganalytics.io/v1/workspaces/{WORKSPACE}/query",
        data=json.dumps({"query": kql}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        body = json.load(resp)
    tables = body.get("tables") or []
    return tables[0]["rows"] if tables else []


def _base(days: int, channel: str | None) -> str:
    where_channel = f'| where tostring(p.channel_id) == "{channel}" ' if channel else ""
    return (
        f"ContainerAppConsoleLogs_CL | where TimeGenerated > ago({days}d) "
        f'| where ContainerAppName_s == "{HOST_APP}" '
        f"| extend p = parse_json(Log_s) | extend ev = tostring(p.event) {where_channel}"
    )


def _bar(fraction: float, width: int = 24) -> str:
    filled = round(fraction * width)
    return "█" * filled + "·" * (width - filled)


def _section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")
    print("─" * 62)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--channel", default=None, help="limita a un channel_id")
    args = ap.parse_args()

    token = _token()
    base = _base(args.days, args.channel)
    verdicts: list[str] = []

    _section(f"SESGO — a quién manda el cerebro (últimos {args.days}d)")
    rows = _query(
        base + '| where ev == "host_dispatched" | summarize n=count() by target=tostring(p.target) | order by n desc',
        token,
    )
    total = sum(r[1] for r in rows) or 0
    if not total:
        print("  sin turnos ruteados en la ventana.")
    else:
        for target, n in rows:
            share = n / total
            print(f"  {target:12} {_bar(share)} {n:5}  {share:6.1%}")
        top_share = rows[0][1] / total
        if top_share >= BIAS_ALERT:
            verdicts.append(
                f"🔴 SESGO: {top_share:.1%} de los turnos van a «{rows[0][0]}». "
                f"Un router que casi siempre contesta lo mismo está colapsado, "
                f"aunque cada decisión suelta se vea limpia."
            )
        else:
            verdicts.append(f"🟢 sesgo: el target dominante lleva {top_share:.1%} (umbral {BIAS_ALERT:.0%}).")

    _section("CONTEXTO — ¿rutea con conversación o a ciegas?")
    rows = _query(
        base + '| where ev == "host_dispatched" '
        "| summarize n=count(), con_ctx=countif(tobool(p.has_context) == true), "
        "lineas=avg(todouble(p.context_lines))",
        token,
    )
    if rows and rows[0][0]:
        n, con_ctx = rows[0][0], rows[0][1] or 0
        # KQL devuelve avg() como string (o vacío) cuando la columna no existe
        # todavía en los logs — el caso exacto de una ventana anterior al deploy
        # que introdujo el campo.
        try:
            lineas = float(rows[0][2] or 0)
        except (TypeError, ValueError):
            lineas = 0.0
        share = con_ctx / n
        print(f"  turnos con contexto : {con_ctx}/{n}  {share:.1%}")
        print(f"  líneas promedio     : {lineas:.1f}" if lineas == lineas else "  líneas promedio     : —")
        if con_ctx == 0:
            verdicts.append(
                "🔴 CONTEXTO: CERO turnos llevaron conversación. RULE 1 del prompt "
                "(continuación, la de máxima prioridad) es inalcanzable y las "
                "continuaciones se están secuestrando. Revisa que el host esté en "
                "v4.32.28+ y que `remember` se esté llamando."
            )
        elif share < CONTEXT_ALERT:
            verdicts.append(f"🟡 contexto: sólo {share:.1%} de los turnos lo llevan.")
        else:
            verdicts.append(f"🟢 contexto: {share:.1%} de los turnos lo llevan.")
    else:
        print("  sin datos — ¿el host ya emite `has_context`? (v4.32.28+)")

    _section("CONTINUIDAD — cambios de persona, y cuáles son sospechosos")
    rows = _query(
        base + '| where ev == "host_dispatched" | where isnotempty(tostring(p.prev_target)) '
        "| summarize n=count(), cambios=countif(tobool(p.switched) == true), "
        "cambios_ciegos=countif(tobool(p.switched) == true and tobool(p.has_context) != true)",
        token,
    )
    if rows and rows[0][0]:
        n, cambios, ciegos = rows[0][0], rows[0][1] or 0, rows[0][2] or 0
        print(f"  turnos con antecedente : {n}")
        print(f"  cambiaron de persona   : {cambios}  ({cambios / n:.1%})")
        print(f"  …de esos, SIN contexto : {ciegos}   ← candidatos a secuestro")
        if ciegos:
            verdicts.append(
                f"🟡 CONTINUIDAD: {ciegos} cambios de persona ocurrieron sin contexto. "
                f"Cada uno es un posible «explica mejor lo anterior» que cayó en quien no traía el hilo."
            )
    else:
        print("  sin antecedentes todavía (el primer turno de cada canal no tiene).")

    _section("ESFUERZO — el effort que el prompt pide, ¿llega?")
    rows = _query(
        base + '| where ev == "host_dispatched" | summarize n=count() by effort=tostring(p.effort) | order by n desc',
        token,
    )
    if rows:
        for effort, n in rows:
            print(f"  {(effort or '(vacío)'):12} {n:5}")
        if len(rows) == 1 and not rows[0][0]:
            verdicts.append("🟡 ESFUERZO: llega vacío siempre — el modelo lo emite y el código lo pierde.")
    else:
        print("  sin datos — el campo `effort` se emite desde v4.32.28.")

    _section("MUDEZ — las ramas de fallo")
    rows = _query(
        base + '| where ev in ("host_dispatch_router_failed","host_router_content_filtered",'
        '"host_router_llm_error","host_dispatch_no_target","host_mention_summon_failed") '
        "| summarize n=count() by ev | order by n desc",
        token,
    )
    if rows:
        for ev, n in rows:
            print(f"  {ev:34} {n:5}")
        verdicts.append(f"🟡 MUDEZ: {sum(r[1] for r in rows)} eventos de fallo del router en la ventana.")
    else:
        print("  ninguna. (Ojo: un cero aquí puede significar 'sano' O 'la rama no")
        print("  puede sonar'. `recovered_without_context` fue INALCANZABLE seis")
        print("  semanas porque nunca había contexto que quitar — un cero que no")
        print("  probaba nada. Ver tests/arch/test_routing_prompt_promises_are_kept.py.")

    _section("VEREDICTO")
    for v in verdicts:
        print(f"  {v}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
