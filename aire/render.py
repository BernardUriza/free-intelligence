"""The thesis, made bytes: the agent's events, turned into HTML the browser
keeps painting as they arrive.

No React, no npm, no build, not one line of JavaScript. Browsers have known how
to render incremental HTML since 1996 — send the `<head>`, then each event as
one more block. The page writes itself because the connection stays open. This
is the "watchability": AIRE's value-add over the raw Claude API — it doesn't
just answer you, you watch it think.
"""

from __future__ import annotations

import html
import json
from typing import Any

import mistune

STYLE = """
:root {
  --paper:#f2f4f7; --card:#fff; --ink:#161a20; --muted:#6a7383;
  --rule:#dde2e9; --say:#2b4aa0; --tool:#8a6210; --tool-bg:#fbf4e4; --meta:#7c8494;
}
@media (prefers-color-scheme:dark){
  :root{ --paper:#0e1116; --card:#161a21; --ink:#e4e8ee; --muted:#8993a2;
         --rule:#252b34; --say:#8fa6ff; --tool:#e0a955; --tool-bg:#231d10; --meta:#79818f; }
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
.wrap{max-width:800px;margin:0 auto;padding:2.5rem 1.25rem 6rem}
header{border-bottom:1px solid var(--rule);padding-bottom:1.25rem;margin-bottom:2rem}
.crumb{font:600 .7rem/1 ui-monospace,SFMono-Regular,Menlo,monospace;
  letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.crumb .mode{color:var(--say)}
h1{margin:.6rem 0 0;font-size:1.5rem;letter-spacing:-.01em;font-weight:600}
h1 span{color:var(--muted);font-weight:400}
.ask{margin-top:1.5rem;padding:.9rem 1.1rem;background:var(--card);
  border:1px solid var(--rule);border-left:3px solid var(--muted);border-radius:3px}
.ask b{display:block;font:600 .65rem/1 ui-monospace,monospace;letter-spacing:.12em;
  text-transform:uppercase;color:var(--muted);margin-bottom:.45rem}
main{display:flex;flex-direction:column;gap:1rem}
main .ask{margin-top:0}
.say{min-width:0}
.say p{margin:0 0 .8rem}.say p:last-child{margin-bottom:0}
.say strong{font-weight:650;color:var(--ink)}
.say em{font-style:italic}
.say a{color:var(--say);text-decoration:underline;text-underline-offset:2px;word-break:break-word}
.say code{background:var(--rule);padding:.1em .35em;border-radius:2px;
  font:.85em ui-monospace,SFMono-Regular,Menlo,monospace}
.say pre{background:var(--card);border:1px solid var(--rule);border-radius:3px;
  padding:.8rem 1rem;overflow-x:auto;margin:0 0 .8rem}
.say pre code{background:none;padding:0}
.say ul,.say ol{margin:0 0 .8rem;padding-left:1.4rem;display:flex;flex-direction:column;gap:.3rem}
.say li::marker{color:var(--muted)}
.say blockquote{margin:0 0 .8rem;padding-left:.9rem;border-left:2px solid var(--rule);color:var(--muted)}
.say h1,.say h2,.say h3{font-size:1rem;font-weight:650;margin:.4rem 0 .5rem}
.tool{background:var(--tool-bg);border:1px solid var(--tool);border-radius:3px;
  padding:.75rem .95rem;font:.8rem/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
  color:var(--tool);overflow-x:auto}
.tool b{font-weight:700;letter-spacing:.02em}
.tool code{display:block;margin-top:.35rem;color:var(--muted);white-space:pre-wrap;word-break:break-word}
.done{margin-top:1.5rem;padding-top:1rem;border-top:1px solid var(--rule);
  font:.75rem/1.7 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--meta)}
.done dt{display:inline;color:var(--muted)}.done dd{display:inline;margin:0 1.25rem 0 .4rem;color:var(--ink)}
.pulse{color:var(--muted);font:.8rem/1 ui-monospace,monospace;letter-spacing:.1em}
form{display:flex;gap:.6rem;margin-top:1.5rem}
input[type=text]{flex:1;padding:.7rem .9rem;background:var(--card);color:var(--ink);
  border:1px solid var(--rule);border-radius:3px;font:inherit}
input[type=text]:focus{outline:2px solid var(--say);outline-offset:1px}
button{padding:.7rem 1.4rem;background:var(--say);color:#fff;border:0;border-radius:3px;
  font:600 .9rem/1 inherit;cursor:pointer}
"""

_markdown = mistune.create_markdown(escape=True)
"""`escape=True`: the agent speaks markdown, but if it spits raw HTML it gets
escaped instead of injected. Its output is model text, not a trusted template."""


def _head(project: str, session: str, mode: str, ask: str | None, status: str) -> str:
    title = f"{html.escape(project)}/{html.escape(session)} — AIRE"
    asked = f'<div class="ask"><b>You asked</b>{html.escape(ask)}</div>' if ask else ""
    return (
        "<!doctype html><html lang=en><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        f"<title>{title}</title><style>{STYLE}</style>"
        '<div class=wrap><header>'
        f'<div class=crumb>project · {html.escape(project)} · mode <span class=mode>{html.escape(mode)}</span></div>'
        f"<h1>{html.escape(session)} <span>— {html.escape(status)}</span></h1>"
        f"{asked}</header><main>"
    )


def _text(delta: str) -> str:
    return f'<div class="say">{_markdown(delta)}</div>'


def _said(text: str) -> str:
    return f'<div class="ask"><b>You asked</b>{html.escape(text)}</div>'


def _tool(name: str, raw: Any) -> str:
    args = html.escape(json.dumps(raw, ensure_ascii=False)[:400]) if raw else ""
    body = f"<code>{args}</code>" if args else ""
    return f'<div class="tool"><b>⟡ {html.escape(name or "?")}</b>{body}</div>'


def _done(result: Any) -> str:
    usage = getattr(result, "usage", None) or {}
    cost = usage.get("total_cost_usd")
    rows = [
        ("session", getattr(result, "session_id", None) or "—"),
        ("tools", str(len(getattr(result, "tool_calls", ()) or ()))),
    ]
    if cost is not None:
        rows.append(("cost", f"${cost:.4f}"))
    cells = "".join(f"<dt>{html.escape(k)}</dt><dd>{html.escape(str(v))}</dd>" for k, v in rows)
    return f'<dl class="done">{cells}</dl>'


def _foot(project: str, session: str, mode: str) -> str:
    action = f"/projects/{html.escape(project)}/sessions/{html.escape(session)}/messages"
    return (
        # The "thinking" pulse turns off without JS: the cascade receives this CSS
        # AFTER the element, so it wins. (Only the stream uses it; the idle
        # landing page doesn't.)
        "<style>.pulse{display:none}</style></main>"
        f'<form method=post action="{action}"><input type=hidden name=mode value="{html.escape(mode)}">'
        '<input type=text name=message placeholder="Continue the conversation…" autofocus required>'
        "<button>Send</button></form></div></html>"
    )


def head(project: str, session: str, mode: str, ask: str | None = None) -> bytes:
    return (
        _head(project, session, mode, ask, "the agent is working")
        + '<div class=pulse>· · · thinking</div>'
    ).encode()


def event(ev: dict[str, Any]) -> bytes:
    kind = ev.get("type")
    if kind == "text":
        return _text(ev.get("text", "")).encode()
    if kind == "tool_call":
        tool = ev.get("tool")
        return _tool(getattr(tool, "name", "?"), getattr(tool, "input", None)).encode()
    if kind == "result":
        return _done(ev.get("result")).encode()
    return b""


def foot(project: str, session: str, mode: str) -> bytes:
    return _foot(project, session, mode).encode()


def transcript(entries: list[dict[str, Any]]) -> str:
    """The Postgres transcript → the conversation, repainted. Entries are opaque
    CLI blobs (the SDK only guarantees type/uuid/timestamp), so they are read
    defensively: what it recognizes it paints, what it doesn't it ignores."""
    out: list[str] = []
    for entry in entries:
        message = entry.get("message") or {}
        role = message.get("role") or entry.get("type")
        content = message.get("content")
        if isinstance(content, str):
            out.append(_said(content) if role == "user" else _text(content))
            continue
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                body = block.get("text", "")
                out.append(_said(body) if role == "user" else _text(body))
            elif block.get("type") == "tool_use":
                out.append(_tool(str(block.get("name", "?")), block.get("input")))
    return "".join(out)


def landing(project: str, session: str, mode: str, entries: list[dict[str, Any]] | None = None) -> bytes:
    n = len(entries or [])
    history = transcript(entries or [])
    status = "no memory yet" if not n else f"{n} entries in memory"
    return (_head(project, session, mode, None, status) + history + _foot(project, session, mode)).encode()
