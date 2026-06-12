"""Prompt construction for the in-character dream diary.

The diary is the user-facing artifact of a consolidation run — Bernard
reads ``!siesta`` and gets a paragraph that sounds like Insult wrote it
half-asleep, not a structured report. Structured numbers are already
in ``fact_consolidation_log``; this is the narrative layer.

System prompt encodes:
- Voice (Insult, Mexican Spanish, dry, no apologies, no AI framing).
- Length cap (60-90 words — diary entry, not essay).
- What to mention (whose facts moved, what the consolidator chose to
  prune vs preserve, anything surprising) and what to OMIT (token
  counts, internal field names, judge errors as technical strings).
- Honesty mandate: if a user failed (``judge_failed``), say so plainly
  — "no terminé de soñar a X" — without exposing the JSON parser stack.
"""

from __future__ import annotations

from personas.insult.core.prompts_loader import load_prompt


def get_diary_system_prompt() -> str:
    """Lazy accessor — re-reads the .md on every call (mtime-cached).
    Lets the operator edit insult/prompts/siesta_diary.md and have the
    next siesta pick it up without restarting."""
    return load_prompt("siesta_diary")


def build_user_prompt(
    *,
    users_total: int,
    users_processed: int,
    failed_users: list[str],
    user_summaries: list[dict],
    duration_ms: int,
) -> str:
    """Render the consolidation report as a user-message for the diarist.

    ``user_summaries`` is a list of dicts shaped like::

        {"name": "Alex", "facts_in": 92, "facts_out": 4,
         "deletes": 88, "updates": 0, "noops": 4, "error": None}

    ``failed_users`` lists the names whose run errored — they are also
    in ``user_summaries`` with ``error`` set, but extracting them up
    front keeps the prompt readable.
    """
    lines = [
        f"Siesta duró {duration_ms // 1000} segundos.",
        f"Procesé {users_processed} de {users_total} usuarios.",
    ]
    if failed_users:
        lines.append(f"No terminé con: {', '.join(failed_users)}.")
    lines.append("")
    lines.append("Por usuario:")
    for u in user_summaries:
        if u.get("error"):
            lines.append(f"- {u['name']}: falló ({u['error']}).")
            continue
        lines.append(
            f"- {u['name']}: tenía {u['facts_in']}, dejé {u['facts_out']}. "
            f"borré {u.get('deletes', 0)}, fusioné {u.get('updates', 0)}, "
            f"dejé en paz {u.get('noops', 0)}."
        )
    lines.append("")
    lines.append("Escribí la entrada del diario.")
    return "\n".join(lines)
