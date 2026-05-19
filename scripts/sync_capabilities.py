#!/usr/bin/env python3
"""Auto-generate Insult's Self-Awareness section in persona.md from code.

Reads tool definitions, detects modules, and injects an up-to-date capabilities
block between <!-- CAPABILITIES:START --> and <!-- CAPABILITIES:END --> markers.

Run via pre-commit hook or manually: python scripts/sync_capabilities.py
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PERSONA = ROOT / "persona.md"
INSULT = ROOT / "insult"

START_MARKER = "<!-- CAPABILITIES:START -->"
END_MARKER = "<!-- CAPABILITIES:END -->"


def extract_tool_names(filepath: Path) -> list[dict]:
    """Extract tool name + first line of description from a *_TOOLS list in a Python file."""
    source = filepath.read_text()
    tree = ast.parse(source)

    tools = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.endswith("_TOOLS") and isinstance(node.value, ast.List):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Dict):
                            name = desc = ""
                            for k, v in zip(elt.keys, elt.values, strict=False):
                                if isinstance(k, ast.Constant) and k.value == "name":
                                    name = v.value if isinstance(v, ast.Constant) else ""
                                if isinstance(k, ast.Constant) and k.value == "description":
                                    desc = _extract_string(v)
                            if name:
                                # First sentence only
                                first_sentence = desc.split(". ")[0] + "." if desc else ""
                                tools.append({"name": name, "desc": first_sentence})
    return tools


def _extract_string(node) -> str:
    """Extract string from AST node (handles JoinedStr, Constant, etc.)."""
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.JoinedStr):
        return "".join(_extract_string(v) for v in node.values)
    return ""


def detect_modules() -> dict[str, bool]:
    """Detect which optional capability modules exist."""
    return {
        "tts": (INSULT / "cogs" / "voice.py").exists(),
        "whisper": (INSULT / "core" / "transcribe.py").exists(),
        "images": (INSULT / "core" / "images.py").exists(),
        "audio": (INSULT / "core" / "audio.py").exists(),
        "reminders": (INSULT / "core" / "reminders.py").exists(),
        "summaries": (INSULT / "core" / "summaries.py").exists(),
        "vectors": (INSULT / "core" / "vectors.py").exists(),
        "web_search": (INSULT / "core" / "llm.py").exists(),
        # Newer capabilities (2026-05) — detect by module presence
        "deep_memory": (INSULT / "core" / "deep_memory.py").exists(),
        "html_artifacts": (INSULT / "core" / "html_artifacts.py").exists(),
        "agent_runner_mcp": (INSULT / "agent" / "mcp_tools.py").exists(),
    }


def detect_fi_core() -> bool:
    """True iff fi-core (shared RAG primitives) is a declared dependency.

    Pre-DM-5 the chunker lived in this codebase; now it's imported from
    the fi-core workspace package in the free-intelligence monorepo
    Bernard maintains. The capability summary should say so — otherwise
    callers asking 'where do you chunk?' get a misleading answer.
    """
    req = ROOT / "requirements.txt"
    if not req.exists():
        return False
    return "fi-core" in req.read_text()


def extract_mcp_tool_names() -> list[dict]:
    """Pull tool names from @tool-decorated functions in mcp_tools.py.

    Each @tool decorator's first positional arg is the tool name; the
    second is its description. Returns names prefixed with
    `mcp__insult_db__` so they match the wire name the agent sees.
    """
    mcp = INSULT / "agent" / "mcp_tools.py"
    if not mcp.exists():
        return []
    try:
        tree = ast.parse(mcp.read_text())
    except SyntaxError:
        return []

    tools: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            for dec in node.decorator_list:
                if (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Name)
                    and dec.func.id == "tool"
                ):
                    name = ""
                    desc = ""
                    if dec.args:
                        name = _extract_string(dec.args[0])
                        if len(dec.args) >= 2:
                            desc = _extract_string(dec.args[1])
                    if name:
                        first_sentence = desc.split(". ")[0] + "." if desc else ""
                        tools.append({
                            "name": f"mcp__insult_db__{name}",
                            "desc": first_sentence,
                        })
    return tools


def build_capabilities_block() -> str:
    """Build the full self-awareness markdown block from code inspection."""
    # Collect tools from all tool definition files
    all_tools = []
    for py_file in sorted(INSULT.rglob("*.py")):
        try:
            tools = extract_tool_names(py_file)
            all_tools.extend(tools)
        except (SyntaxError, UnicodeDecodeError):
            continue

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

    if modules["summaries"]:
        lines.append(
            "- **Cross-channel awareness**: You know what's happening in other channels via periodic summaries."
        )

    if modules["vectors"]:
        lines.append("- **Semantic memory**: You search user facts by meaning, not just keywords.")

    if modules["deep_memory"]:
        lines.append(
            "- **Deep vector memory**: Beyond the structured fact digest, you can vector-recall "
            "the actual chunks of past conversation that semantically match a query. "
            "Powered by `mcp__insult_db__deep_memory(user_id, query, top_k)`. "
            "Backed by Azure OpenAI ada-002 embeddings + Postgres pgvector."
        )

    if modules["html_artifacts"]:
        lines.append(
            "- **HTML artifact publishing**: You can mint shareable HTML pages "
            "(reports, mini-apps, snapshots) served at `bot.bernarduriza.com/a/{id}`. "
            "Powered by `mcp__insult_db__publish_html_artifact(title, html_content, user_id)`. "
            "Use for content that wouldn't fit in chat or that renders better as a page."
        )

    lines.append(
        "- **DMs**: Users can DM you directly by clicking on your profile in Discord. "
        'Encourage them: "Dime por DM si quieres hablar en privado."'
    )

    # MCP tools come from the agent runner side (registered in
    # insult/agent/mcp_tools.py via @tool decorators).
    mcp_tools = extract_mcp_tool_names() if modules.get("agent_runner_mcp") else []

    # Add tool-specific capabilities
    if all_tools or mcp_tools:
        lines.append("")
        lines.append("### Available Tools")
        for tool in all_tools:
            lines.append(f"- `{tool['name']}`: {tool['desc']}")
        for tool in mcp_tools:
            lines.append(f"- `{tool['name']}`: {tool['desc']}")

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
            "- **Azure Database for PostgreSQL + pgvector** — your data plane. "
            "Cero blob, cero on-prem dependency."
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
    """Inject capabilities block into persona.md. Returns True if content changed."""
    content = PERSONA.read_text()
    new_block = build_capabilities_block()

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
        PERSONA.write_text(new_content)
        return True
    return False


if __name__ == "__main__":
    changed = sync()
    if changed:
        print("sync_capabilities: persona.md updated")
        sys.exit(0)
    else:
        print("sync_capabilities: persona.md already up to date")
        sys.exit(0)
