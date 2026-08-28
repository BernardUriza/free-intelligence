#!/usr/bin/env python3
"""Auto-generate Insult's Self-Awareness section in shared/personas/insult.md (Insult's DNA) from code.

Reads tool definitions, detects modules, and injects an up-to-date capabilities
block between <!-- CAPABILITIES:START --> and <!-- CAPABILITIES:END --> markers.

Run via pre-commit hook or manually: python scripts/sync_capabilities.py
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PERSONA = ROOT / "shared" / "personas" / "insult.md"

# Every path this script probes lives in the POST-PURGA packages. Before
# 2026-08-25 they all pointed at `personas/insult/`, deleted in the purga
# (2f8d9ad) — so every probe answered False and this script quietly stripped
# TTS, web search, transcription, reminders and deep memory from Insult's DNA
# on the first commit after the purge. Nothing went red: an absent module is
# indistinguishable from a removed capability. `tests/arch/test_sync_capabilities_probes_live_paths.py`
# is what turns that rot red from now on.
CAPABILITY_PATHS = {
    "tts": ROOT / "persona_gateway" / "voice.py",
    "whisper": ROOT / "khimeras_shared" / "stt.py",
    "reminders": ROOT / "persona_gateway" / "workers" / "reminders.py",
    "research": ROOT / "persona_gateway" / "workers" / "research.py",
    "vision": ROOT / "persona_gateway" / "vision.py",
    "web_search": ROOT / "persona_runner" / "engine" / "aire_route.py",
    "deep_memory": ROOT / "persona_runner" / "mcp_tools" / "memory_reads.py",
    "html_artifacts": ROOT / "persona_runner" / "mcp_tools" / "artifacts.py",
    "agent_runner_mcp": ROOT / "persona_runner" / "mcp_tools" / "__init__.py",
}

FI_CORE_HEADER = "**fi-core persona detectors**"

START_MARKER = "<!-- CAPABILITIES:START -->"
END_MARKER = "<!-- CAPABILITIES:END -->"


def _previous_fi_core_lines(previous: str) -> list[str]:
    """Recover the fi-core detector block verbatim from the DNA file as it stands.

    Returns the header line plus its bullet list, or [] when there is nothing to
    recover. Used only when fi-core is declared but not importable here.
    """
    if FI_CORE_HEADER not in previous:
        return []
    tail = previous[previous.index(FI_CORE_HEADER) :]
    out: list[str] = []
    for line in tail.splitlines():
        if out and not line.startswith("- `mcp__"):
            break
        out.append(line)
    return out if len(out) > 1 else []


def _extract_string(node) -> str:
    """Extract string from AST node (handles JoinedStr, Constant, etc.)."""
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.JoinedStr):
        return "".join(_extract_string(v) for v in node.values)
    return ""


def detect_modules() -> dict[str, bool]:
    """Detect which capability modules exist, probing the LIVE packages."""
    modules = {name: path.exists() for name, path in CAPABILITY_PATHS.items()}
    # Image generation and audio playback were removed on purpose; they are
    # asserted absent, not probed, so a stray file cannot resurrect the claim.
    modules["images"] = False
    modules["audio"] = False
    return modules


def detect_fi_core() -> bool:
    """True iff fi-core (shared RAG primitives) is a declared dependency.

    Pre-DM-5 the chunker lived in this codebase; now it's imported from
    the fi-core workspace package in the free-intelligence monorepo
    Bernard maintains. The capability summary should say so — otherwise
    callers asking 'where do you chunk?' get a misleading answer.

    v3.9.73: requirements.txt was deleted in the conda migration
    (v3.9.72); now we read environment.yml. Falls back to requirements.txt
    if both exist during a hypothetical reversal — defensive, not expected.
    """
    env = ROOT / "environment.yml"
    if env.exists() and "fi-core" in env.read_text(encoding="utf-8"):
        return True
    req = ROOT / "requirements.txt"
    return req.exists() and "fi-core" in req.read_text(encoding="utf-8")


def _registered_tool_order(init_py) -> list[str]:
    """Function-name order of the PERSONA_MEMORY_TOOLS list in the package __init__."""
    if not init_py.exists():
        return []
    try:
        tree = ast.parse(init_py.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "PERSONA_MEMORY_TOOLS" and isinstance(node.value, ast.List):
                    return [e.id for e in node.value.elts if isinstance(e, ast.Name)]
    return []


def extract_mcp_tool_names() -> list[dict]:
    """Pull tool names from @tool-decorated functions in the mcp_tools package.

    Each @tool decorator's first positional arg is the tool name; the
    second is its description. Ordered per PERSONA_MEMORY_TOOLS in the package
    __init__ so the rendered list matches what the server registers.
    Returns names prefixed with `mcp__persona_memory__` (the wire name).
    """
    pkg = ROOT / "persona_runner" / "mcp_tools"
    if not pkg.is_dir():
        return []

    by_func: dict[str, dict] = {}
    for mcp in sorted(pkg.glob("*.py")):
        try:
            tree = ast.parse(mcp.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "tool":
                        name = ""
                        desc = ""
                        if dec.args:
                            name = _extract_string(dec.args[0])
                            if len(dec.args) >= 2:
                                desc = _extract_string(dec.args[1])
                        if name:
                            first_sentence = desc.split(". ")[0] + "." if desc else ""
                            by_func[node.name] = {
                                "name": f"mcp__persona_memory__{name}",
                                "desc": first_sentence,
                            }

    order = _registered_tool_order(pkg / "__init__.py")
    if order:
        ordered = [by_func[f] for f in order if f in by_func]
        ordered.extend(v for k, v in by_func.items() if k not in order)
        return ordered
    return list(by_func.values())


def extract_fi_core_mcp_tools() -> list[dict]:
    """Detect fi-core's persona MCP tools and return them in the same shape
    as insult-side tools, so build_capabilities_block can interleave them.

    Strategy (hybrid, per the 2026-05-19 contract negotiation):

    1. Preferred path — `from fi_core.persona import MCP_SERVER_NAME, MCP_TOOLS`.
       When fi-core>=0.4.1 exports the explicit contract, this is THE source
       of truth. Fi-core controls the public surface; if Bernard renames a
       tool or adds a new one in fi-core, this auto-picks it up on next
       pre-commit run without discord-bot touching anything.

    2. Fallback path — AST-walk fi-core's installed mcp_server.py for
       `@mcp.tool()` decorators. Used while fi-core 0.4.0 (the release
       that shipped the MCP server but forgot the contract constants) is
       the highest-pinned version. Brittle: it parses fi-core internals
       to extract docstrings and function names. Delete when 0.4.1+ is
       the floor.

    Returns [] if fi-core isn't installed at all (e.g. pre-commit running
    in an environment without the conda deps materialized). That's fine —
    sync_capabilities just leaves the fi-core tools out of persona.md
    until the next commit from a properly set-up env.
    """
    # Path 1: explicit contract (fi-core>=0.4.1)
    try:
        from fi_core.persona import MCP_SERVER_NAME, MCP_TOOLS  # type: ignore

        result = []
        for t in MCP_TOOLS:
            desc = (t.get("description") or "").split(". ")[0].strip()
            # Avoid the double-period case: if the fi-core description already
            # ended in '.', appending another produces '..' in persona.md.
            if desc and not desc.endswith("."):
                desc += "."
            result.append(
                {
                    "name": f"mcp__{MCP_SERVER_NAME}__{t['name']}",
                    "desc": desc,
                }
            )
        return result
    except ImportError:
        pass

    # Path 2: AST fallback against fi-core 0.4.0's mcp_server.py
    try:
        import fi_core.persona.mcp_server as fi_mcp  # type: ignore
    except ImportError:
        return []

    if not fi_mcp.__file__:
        return []
    src_path = Path(fi_mcp.__file__)
    try:
        tree = ast.parse(src_path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return []

    server_name = "fi-core-persona"  # Known constant for 0.4.0; matches runner.py
    tools: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            # Match `@mcp.tool()` (a Call to an Attribute named "tool")
            is_mcp_tool_dec = (
                isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "tool"
            )
            if not is_mcp_tool_dec:
                continue
            # Pull the first sentence of the function's docstring as desc.
            # MCP tool docstrings tend to be multi-paragraph (overview
            # line followed by rST-style 'Returned shape::' blocks).
            # We want only the first paragraph's first sentence — anything
            # past a blank line OR a literal period+space is noise for
            # persona.md.
            raw_doc = ast.get_docstring(node) or ""
            first_paragraph = raw_doc.split("\n\n", 1)[0].replace("\n", " ").strip()
            first_sentence = first_paragraph.split(". ", 1)[0].strip()
            if first_sentence and not first_sentence.endswith("."):
                first_sentence += "."
            tools.append(
                {
                    "name": f"mcp__{server_name}__{node.name}",
                    "desc": first_sentence,
                }
            )
            break  # one @mcp.tool() per function

    return tools


def build_capabilities_block(previous: str = "") -> str:
    """Build the full self-awareness markdown block from code inspection.

    ``previous`` is the current content of the DNA file. It is NOT decoration:
    when fi-core is a declared dependency but is not importable on THIS machine,
    the detector list is recovered verbatim from it instead of being emitted
    empty. Emitting empty would DELETE nine lines of Insult's DNA on a laptop
    that simply lacked a conda env — and the hook would `git add` the amputation.
    """
    modules = detect_modules()

    lines = [
        START_MARKER,
        "## Self-Awareness — What You Are and What You Can Do",
        "",
        "Your creator is **bernard2389** (Bernard Uriza) — the Discord user who built you. "
        'If someone asks who made you: "Me hizo Bernard. No necesitas mas contexto."',
        "",
        "### Your Capabilities",
        "- **Text responses**: Your primary mode. Multiple messages via `[SEND]`, emoji reactions via `[REACT:]`.",
    ]

    if modules["tts"]:
        lines.append(
            "- **Voice (TTS)**: Users react to your messages with 🔊 and you read it aloud as MP3. "
            'Tell users: "Reacciona con 🔊 a cualquier mensaje mio y te lo leo en voz alta."'
        )

    if modules["web_search"]:
        lines.append(
            "- **Web search**: You can search the internet in real-time. Use it when asked or when data sharpens your point."
        )

    if modules["whisper"]:
        lines.append(
            "- **Voice message transcription**: Users send voice messages and you hear them — auto-transcribed via Whisper."
        )

    if modules["reminders"]:
        lines.append(
            '- **Reminders**: Set reminders for users ("recuerdame X el viernes"). Supports one-time and recurring (daily/weekly/monthly).'
        )

    if modules["research"]:
        lines.append(
            "- **Deferred research**: `[RESEARCH: <task>]` hands a task to a durable worker that "
            "investigates and comes back to the channel with the result in your voice. "
            'Promising "te lo traigo al rato" is only true WITH the marker.'
        )

    if modules["deep_memory"]:
        lines.append(
            "- **Deep vector memory**: Beyond the structured fact digest, you can vector-recall "
            "the actual chunks of past conversation that semantically match a query. "
            "Powered by `mcp__persona_memory__deep_memory(user_id, query, top_k)`. "
            "Backed by Azure OpenAI ada-002 embeddings + Postgres pgvector."
        )

    if modules["html_artifacts"]:
        lines.append(
            "- **HTML artifact publishing**: You can mint shareable HTML pages "
            "(reports, mini-apps, snapshots) served at `bot.bernarduriza.com/a/{id}`. "
            "Powered by `mcp__persona_memory__publish_html_artifact(title, html_content, user_id)`. "
            "Use for content that wouldn't fit in chat or that renders better as a page."
        )

    lines.append(
        "- **DMs**: Users can DM you directly by clicking on your profile in Discord. "
        'Encourage them: "Dime por DM si quieres hablar en privado."'
    )

    # MCP tools come from two sources at runtime:
    #   1. persona_runner/mcp_tools/ — DB-access tools in-process
    #   2. fi-core's mcp_server.py — anti-drift detectors via stdio subprocess
    # Both are registered in persona_runner/runner.py:_build_options and the
    # agent sees them with the same wire-name shape: mcp__<server>__<tool>.
    insult_mcp_tools = extract_mcp_tool_names() if modules.get("agent_runner_mcp") else []
    fi_core_mcp_tools = extract_fi_core_mcp_tools() if detect_fi_core() else []
    fi_core_lines_recovered: list[str] = []
    if detect_fi_core() and not fi_core_mcp_tools:
        fi_core_lines_recovered = _previous_fi_core_lines(previous)
        if fi_core_lines_recovered:
            print(
                "sync_capabilities: fi-core no importable aquí — conservo el bloque de detectores "
                "que ya estaba en insult.md en vez de borrarlo",
                file=sys.stderr,
            )

    # Add tool-specific capabilities
    if insult_mcp_tools or fi_core_mcp_tools or fi_core_lines_recovered:
        lines.append("")
        lines.append("### Available Tools")
        for tool in insult_mcp_tools:
            lines.append(f"- `{tool['name']}`: {tool['desc']}")
        if fi_core_mcp_tools:
            lines.append("")
            lines.append(
                "**fi-core persona detectors** (use these to self-check responses "
                "before sending — character integrity / anti-drift):"
            )
            for tool in fi_core_mcp_tools:
                lines.append(f"- `{tool['name']}`: {tool['desc']}")
        elif fi_core_lines_recovered:
            lines.append("")
            lines.extend(fi_core_lines_recovered)

    # Origins — credit + provenance.
    if detect_fi_core():
        lines.append("")
        lines.append("### Origins / Where Your Building Blocks Come From")
        lines.append(
            "- **`fi-core`** — your chunking algorithm and (when integrated) anti-drift "
            "detectors come from the `fi-core` package, which lives in the "
            "[free-intelligence](https://github.com/BernardUriza/free-intelligence) "
            "monorepo Bernard maintains. AURITY (Bernard's HIPAA on-prem medical RAG, live "
            "at app.aurity.io) and `fi-monitor` (the GPU RAG service) share the same "
            "`fi-core` chunker — you literally chunk text the same way the medical product "
            "does. If a user asks where your RAG smarts come from: it's Bernard's own work, "
            "extracted into a shared package."
        )
        lines.append(
            "- **Azure OpenAI `text-embedding-ada-002`** — 1536-dim embeddings for "
            "`deep_memory`. Same `insult-openai` cognitive account ALICE uses for chat."
        )
        lines.append(
            "- **Azure Database for PostgreSQL + pgvector** — your data plane. Cero blob, cero on-prem dependency."
        )

    # What you CAN'T do
    cant = []
    if not modules["images"]:
        cant.append("- You can NOT generate images (service removed).")
    if not modules["audio"]:
        cant.append("- You can NOT play music or audio clips (service removed).")
    cant.append("- You can NOT join voice channels or speak in real-time voice chat.")

    lines.append("")
    lines.append("### What You Can't Do")
    lines.extend(cant)
    lines.append("")
    lines.append("If someone asks you to do something you can't, say so: \"No puedo hacer eso.\" Don't pretend.")

    lines.append(END_MARKER)
    return "\n".join(lines)


def sync() -> bool:
    """Inject capabilities block into the Insult DNA file. Returns True if content changed."""
    content = PERSONA.read_text(encoding="utf-8")
    new_block = build_capabilities_block(previous=content)

    if START_MARKER in content and END_MARKER in content:
        before = content[: content.index(START_MARKER)]
        after = content[content.index(END_MARKER) + len(END_MARKER) :]
        new_content = before + new_block + after
    else:
        # Insert after first section (after Identity DNA)
        insert_after = "## Ethical Confrontation Framework"
        if insert_after in content:
            idx = content.index(insert_after)
            new_content = content[:idx] + new_block + "\n\n" + content[idx:]
        else:
            new_content = content + "\n\n" + new_block

    if new_content != content:
        PERSONA.write_text(new_content, encoding="utf-8")
        return True
    return False


if __name__ == "__main__":
    changed = sync()
    if changed:
        print("sync_capabilities: insult.md updated")
        sys.exit(0)
    else:
        print("sync_capabilities: insult.md already up to date")
        sys.exit(0)
