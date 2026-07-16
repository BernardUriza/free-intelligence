"""CLINICAL GUARD (defense in depth) — the code layer that protects Alex's cluster.

The judge prompt BEGS the model never to delete health/trauma facts; a prompt is
a plea, not a guarantee — a small model on a bad day will still hand back
``{"op":"DELETE","id":17}`` for "tiene CPTSD". So the applier REFUSES it in
code: a destructive op (DELETE, or an UPDATE that consumes the fact into a
merge) on a clinical fact is rejected and logged, regardless of what the judge
asked for. Non-clinical ops in the same plan still apply — the guard protects
the cluster, it does not freeze consolidation.
"""

from __future__ import annotations

import re

from khimeras_shared.behavior.vulnerability import matched_signal_groups

CLINICAL_CATEGORIES = frozenset(
    {
        "health",
        "salud",
        "medical",
        "medico",
        "médico",
        "mental_health",
        "salud_mental",
        "trauma",
        "safety",
        "seguridad",
        "medication",
        "medicacion",
        "medicación",
        "diagnosis",
        "diagnostico",
        "diagnóstico",
    }
)

# Text-level net, on top of `behavior.vulnerability`'s signal groups (diagnoses,
# psychiatric meds, clinicians, hospitalization, self-harm, chronic comorbidity):
# the plainly-medical vocabulary those groups don't carry.
_CLINICAL_TEXT_RE = re.compile(
    r"(?i)\b("
    r"diagn[oó]stic\w*|diagnos\w*|"
    r"medicaci[oó]n|medicament\w*|f[aá]rmac\w*|pastill\w*|dosis|mg\b|receta\w*|"
    r"tratamiento\w*|terapia\w*|therapy|"
    r"enfermedad\w*|padecimient\w*|s[ií]ntoma\w*|cr[oó]nic\w*|"
    r"vih|hiv|hepatitis|c[aá]ncer|cancer|diabet\w*|epileps\w*|"
    r"depresi[oó]n|ansiedad|anxiety|depress\w*|"
    r"abuso|abuse|violaci[oó]n|maltrat\w*|"
    r"cl[ií]nica|hospital\w*|imss|consulta m[eé]dica|"
    r"alerg\w*|antirretrovir\w*|arv\b"
    r")"
)


def is_clinical_fact(fact: dict) -> str | None:
    """Reason string when the fact is clinical/traumatic, else None.

    Deliberately over-inclusive: a false positive costs one redundant fact kept
    forever; a false negative costs someone's diagnosis (the 2026-06-03 P0).
    """
    category = (fact.get("category") or "").strip().lower()
    if category in CLINICAL_CATEGORIES:
        return f"category={category}"
    text = fact.get("fact") or ""
    groups = matched_signal_groups([fact])
    if groups:
        return f"vulnerability_signal={','.join(groups)}"
    if _CLINICAL_TEXT_RE.search(text):
        return "clinical_text"
    return None


def filter_clinical_destruction(plan: list[dict], by_id: dict[int, dict]) -> tuple[list[dict], list[dict]]:
    """Strip every destructive op that would touch a clinical fact.

    Returns `(safe_plan, blocked_ops)`. A blocked DELETE becomes a NOOP; a blocked
    UPDATE (merge) is dropped and each of its `merge_ids` becomes a NOOP, so the
    plan still references every input fact exactly once (fi-core's contract) and
    nothing clinical is destroyed. Everything else passes through untouched — a
    plan may still fold "le gusta el café" into one line.
    """
    safe: list[dict] = []
    blocked: list[dict] = []
    for op in plan:
        kind = op.get("op")
        if kind == "DELETE":
            fact = by_id.get(op.get("id"))
            reason = is_clinical_fact(fact) if fact else None
            if reason:
                blocked.append(op)
                safe.append({"op": "NOOP", "id": op["id"], "reason": f"clinical_guard: {reason}"})
                continue
        elif kind == "UPDATE":
            merge_ids = op.get("merge_ids", [])
            hits = [(fid, is_clinical_fact(by_id[fid])) for fid in merge_ids if fid in by_id]
            clinical = [(fid, r) for fid, r in hits if r]
            if clinical:
                blocked.append(op)
                for fid in merge_ids:
                    reason = dict(clinical).get(fid) or "merged with a clinical fact"
                    safe.append({"op": "NOOP", "id": fid, "reason": f"clinical_guard: {reason}"})
                continue
        safe.append(op)
    return safe, blocked
