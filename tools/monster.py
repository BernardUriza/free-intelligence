"""The monster — a local waiter that draws the directly-follows graph of the log.

Process mining's oldest trick, applied to ``aire_log``: every event type is a
node, every "B came right after A" is an edge, and the edge grows fatter the
more times it happened. The tangle that comes out is the *figure* of the system
— what the literature calls a spaghetti model when the process is wild.

This is a WAITER in the repo's sense ([[log-is-the-truth]]): it only READS the
append-only truth in the owner's Postgres and derives a view — a self-contained
HTML file with inline SVG, no CDN, no build, openable from disk. The daemon
never knows it exists; that is the point. Delete the output and nothing is
lost; re-run it next year over a million rows and the same SELECT feeds it.

Usage::

    export AIRE_DATABASE_URL=postgresql://...   # the pen's DSN (read-only use)
    python tools/monster.py [-o monster.html]

The parser here is deliberately tiny: it classifies a line into an event type
(KEEPALIVE, MESSAGE POS, CONNECT, PEN-UP, ...) and nothing more. Intelligence
stays out of the daemon; a waiter is allowed to squint.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import math
import os
import re
import sys
from collections import Counter

EVENT_RE = re.compile(r"^[A-Z][A-Z0-9-]*$")

PALETTE = [
    ("#2a78d6", "#3987e5"),
    ("#1baf7a", "#199e70"),
    ("#eda100", "#c98500"),
    ("#008300", "#008300"),
    ("#4a3aa7", "#9085e9"),
    ("#e34948", "#e66767"),
    ("#e87ba4", "#d55181"),
    ("#eb6834", "#d95926"),
]
MUTED = ("#898781", "#898781")


def classify(line: str) -> str | None:
    """`2026-07-14T03:23:33 127.0.0.1:57180 app-demo-device-01 KEEPALIVE seq=1`
    → `KEEPALIVE`; `... MESSAGE SPEED 118kmh` → `MESSAGE SPEED`. Lines whose
    tokens never look like an event keyword (garbage from the open port) fold
    into OTHER rather than polluting the node set."""
    tokens = line.split()
    for i, tok in enumerate(tokens[1:], start=1):
        if EVENT_RE.match(tok):
            if tok == "MESSAGE" and i + 1 < len(tokens) and EVENT_RE.match(tokens[i + 1]):
                return f"MESSAGE {tokens[i + 1]}"
            return tok
    return "OTHER" if len(tokens) > 2 else None


async def fetch_lines(dsn: str) -> list[tuple[int, str]]:
    import asyncpg

    conn = await asyncpg.connect(dsn)
    try:
        rows = await conn.fetch("SELECT seq, line FROM aire_log ORDER BY seq")
        return [(r["seq"], r["line"]) for r in rows]
    finally:
        await conn.close()


def build_graph(lines: list[tuple[int, str]]):
    events = [(seq, kind) for seq, raw in lines if (kind := classify(raw))]
    node_counts: Counter[str] = Counter(kind for _, kind in events)
    edge_counts: Counter[tuple[str, str]] = Counter(
        (a[1], b[1]) for a, b in zip(events, events[1:])
    )
    return node_counts, edge_counts, len(events)


def layout(nodes: list[str], cx: float, cy: float, r: float) -> dict[str, tuple[float, float]]:
    step = 2 * math.pi / max(len(nodes), 1)
    return {
        name: (cx + r * math.cos(i * step - math.pi / 2), cy + r * math.sin(i * step - math.pi / 2))
        for i, name in enumerate(nodes)
    }


def render(node_counts, edge_counts, total: int, span: str) -> str:
    nodes = [name for name, _ in node_counts.most_common()]
    colored = [n for n in nodes if n not in ("LISTENING", "OTHER")]
    colors = {name: MUTED for name in nodes}
    colors.update({name: PALETTE[i] for i, name in enumerate(colored[: len(PALETTE)])})

    W, H, CX, CY, R = 920, 700, 460, 375, 235
    pos = layout(nodes, CX, CY, R)
    max_edge = max(edge_counts.values())
    max_node = max(node_counts.values())

    def width(count: int) -> float:
        return 1.5 + 6.5 * math.log1p(count) / math.log1p(max_edge)

    def radius(count: int) -> float:
        return 14 + 18 * math.sqrt(count / max_node)

    edges_svg, labels_svg = [], []
    for (a, b), count in sorted(edge_counts.items(), key=lambda kv: kv[1]):
        w = width(count)
        if a == b:
            x, y = pos[a]
            r_node = radius(node_counts[a])
            r_loop = r_node * 0.9
            path = (
                f"M {x - 6:.1f} {y - r_node + 2:.1f} "
                f"a {r_loop:.1f} {r_loop:.1f} 0 1 1 12 0"
            )
            lx, ly = x + r_loop + 16, y - r_node - r_loop
        else:
            x1, y1 = pos[a]
            x2, y2 = pos[b]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            bend = 0.18 if (b, a) in edge_counts else 0.06
            qx, qy = mx + (CX - mx) * -bend * 2, my + (CY - my) * -bend * 2
            r1, r2 = radius(node_counts[a]) + 3, radius(node_counts[b]) + 6
            d1 = math.hypot(qx - x1, qy - y1) or 1
            d2 = math.hypot(x2 - qx, y2 - qy) or 1
            x1, y1 = x1 + (qx - x1) * r1 / d1, y1 + (qy - y1) * r1 / d1
            x2, y2 = x2 - (x2 - qx) * r2 / d2, y2 - (y2 - qy) * r2 / d2
            path = f"M {x1:.1f} {y1:.1f} Q {qx:.1f} {qy:.1f} {x2:.1f} {y2:.1f}"
            lx, ly = (mx + qx) / 2, (my + qy) / 2
        edges_svg.append(
            f'<path class="edge" d="{path}" stroke-width="{w:.1f}" '
            f'marker-end="url(#arrow)"><title>{html.escape(a)} → {html.escape(b)}: '
            f"{count}×</title></path>"
        )
        if count >= max(2, max_edge // 200):
            labels_svg.append(
                f'<text class="edge-label" x="{lx:.1f}" y="{ly:.1f}">{count}</text>'
            )

    nodes_svg = []
    for name in nodes:
        x, y = pos[name]
        r = radius(node_counts[name])
        light, dark = colors[name]
        below = y + r + 16
        nodes_svg.append(
            f'<g class="node"><circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
            f'style="--c-light:{light};--c-dark:{dark}">'
            f"<title>{html.escape(name)}: {node_counts[name]} events</title></circle>"
            f'<text class="node-label" x="{x:.1f}" y="{below:.1f}">{html.escape(name)}</text>'
            f'<text class="node-count" x="{x:.1f}" y="{below + 14:.1f}">{node_counts[name]}</text></g>'
        )

    table_rows = "".join(
        f"<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td><td>{c}</td></tr>"
        for (a, b), c in edge_counts.most_common()
    )

    return f"""<!doctype html>
<meta charset="utf-8">
<title>AIRE — the monster</title>
<style>
  :root {{
    color-scheme: light dark;
    --surface: #fcfcfb; --page: #f9f9f7; --ink: #0b0b0b; --ink-2: #52514e;
    --muted: #898781; --hairline: #e1e0d9; --edge: #c3c2b7;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --surface: #1a1a19; --page: #0d0d0d; --ink: #ffffff; --ink-2: #c3c2b7;
      --hairline: #2c2c2a; --edge: #383835;
    }}
  }}
  body {{ margin: 0; background: var(--page); color: var(--ink);
         font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ max-width: 980px; margin: 0 auto; padding: 24px 16px 48px; }}
  h1 {{ font-size: 20px; margin: 0 0 2px; }}
  .sub {{ color: var(--ink-2); margin: 0 0 16px; }}
  figure {{ margin: 0; background: var(--surface); border: 1px solid var(--hairline);
            border-radius: 8px; padding: 8px; overflow-x: auto; }}
  svg {{ display: block; margin: 0 auto; }}
  .edge {{ fill: none; stroke: var(--edge); opacity: .85; }}
  .edge:hover {{ stroke: var(--ink-2); opacity: 1; }}
  circle {{ fill: var(--c-light); }}
  @media (prefers-color-scheme: dark) {{ circle {{ fill: var(--c-dark); }} }}
  .node-label {{ fill: var(--ink); font-size: 12px; font-weight: 600; text-anchor: middle; }}
  .node-count {{ fill: var(--ink-2); font-size: 11px; text-anchor: middle; }}
  .edge-label {{ fill: var(--muted); font-size: 10px; text-anchor: middle;
                 paint-order: stroke; stroke: var(--surface); stroke-width: 3px; }}
  #arrow path {{ fill: var(--edge); }}
  details {{ margin-top: 16px; }}
  table {{ border-collapse: collapse; margin-top: 8px; }}
  td, th {{ border-bottom: 1px solid var(--hairline); padding: 4px 12px 4px 0;
            text-align: left; font-variant-numeric: tabular-nums; }}
  th {{ color: var(--ink-2); font-weight: 600; }}
</style>
<main>
  <h1>The monster 🌬️</h1>
  <p class="sub">Directly-follows graph of <code>aire_log</code> — {total} events, {span}.
     A node is an event type; an edge means "this followed that", fatter = more often.
     The truth lives in Azure Postgres; this page is a waiter.</p>
  <figure>
    <svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"
         aria-label="Directly-follows graph of AIRE's event log">
      <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
        markerWidth="9" markerHeight="9" orient="auto-start-reverse"
        markerUnits="userSpaceOnUse">
        <path d="M 0 0 L 10 5 L 0 10 z"/></marker></defs>
      {"".join(edges_svg)}
      {"".join(labels_svg)}
      {"".join(nodes_svg)}
    </svg>
  </figure>
  <details>
    <summary>Every transition, as a table</summary>
    <table><tr><th>from</th><th>to</th><th>count</th></tr>{table_rows}</table>
  </details>
</main>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Draw the directly-follows graph of aire_log as a self-contained HTML."
    )
    parser.add_argument("-o", "--out", default="monster.html")
    args = parser.parse_args()

    dsn = os.environ.get("AIRE_DATABASE_URL", "")
    if not dsn:
        sys.exit("AIRE_DATABASE_URL is not set — the waiter has nothing to read.")

    lines = asyncio.run(fetch_lines(dsn))
    if not lines:
        sys.exit("aire_log is empty — no monster yet.")
    node_counts, edge_counts, total = build_graph(lines)
    first_ts, last_ts = lines[0][1].split()[0], lines[-1][1].split()[0]
    span = f"{first_ts} → {last_ts} UTC"

    doc = render(node_counts, edge_counts, total, span)
    with open(args.out, "w") as f:
        f.write(doc)
    print(f"monster drawn: {args.out}")
    print(json.dumps({"events": total, "nodes": dict(node_counts.most_common())}, indent=2))


if __name__ == "__main__":
    main()
