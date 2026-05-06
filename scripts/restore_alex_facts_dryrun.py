"""Dry-run: re-derive Alex's lost vulnerability facts from his message history.

Context (2026-05-05): Alex's clinical fact cluster (CPTSD, quetiapina,
sertralina, neuropsiquiatra, artritis, internamiento) was wiped from prod
on 2026-04-27 when a container swap downloaded a stale 4-fact blob over
his 92-fact local DB. The blob storage account has no versioning and no
soft-delete, so the facts cannot be recovered from any backup.

But the source `messages` rows are still in the DB. This script proposes
fact re-insertions that are each anchored to a verbatim message Alex sent,
prints the SQL it would run, and computes the resulting vulnerability
score under the new dedupe-by-signal-group rule. **It does NOT execute
any writes.** The operator must inspect the proposed facts and run a
companion `apply` script with explicit confirmation.

Usage:
    python scripts/restore_alex_facts_dryrun.py /path/to/memory.db

Exit code is non-zero if the local DB does not contain Alex's user_id or
if any of the source-message timestamps cannot be located (i.e. the
citation is no longer verifiable).
"""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

ALEX_USER_ID = "1431300030823927999"


@dataclass(frozen=True)
class ProposedFact:
    """A single fact to insert with the message that supports it.

    The excerpt must appear verbatim somewhere in Alex's message history —
    the dry-run looks it up via substring match across all his messages
    rather than by exact timestamp (SQLite float-precision rounds the .15
    digit so direct timestamp equality is unreliable). The matching
    message's timestamp is reported back so the operator can audit the
    citation."""

    category: str
    fact: str
    source_excerpt: str  # the words in Alex's message that justify this fact


# Each proposed fact is keyed to a real message Alex sent. The excerpt must
# be a substring of the message at `source_message_ts` — the dry-run
# verifies this and refuses to print otherwise.
PROPOSED_FACTS: list[ProposedFact] = [
    ProposedFact(
        category="personal",
        fact="Tiene Estrés Postraumático Complejo (CPTSD)",
        source_excerpt="Estrés Postraumático Complejo",
    ),
    ProposedFact(
        category="personal",
        fact="Toma quetiapina y sertralina recetadas por su neuropsiquiatra",
        source_excerpt="Me aumentó dosis de quetiapina y sertralina",
    ),
    ProposedFact(
        category="personal",
        fact="Está en tratamiento activo con neuropsiquiatra desde hace varios años",
        source_excerpt="Tengo una neuropsiquiatra muy chingona que me atiende pro bono desde hace varios años",
    ),
    ProposedFact(
        category="personal",
        fact="Tiene artritis en proceso de diagnóstico y posibles condiciones autoinmunes",
        source_excerpt="artritis en proceso de diagnóstico y otras posibles condiciones autoinmunes",
    ),
    ProposedFact(
        category="incidents",
        fact="Estuvo a punto de internamiento psiquiátrico antes del ajuste de medicación",
        source_excerpt="Estaba en un estado ya muy complejo a punto de in internamiento",
    ),
    ProposedFact(
        category="personal",
        fact="Le diagnosticaron TDA en su época universitaria",
        source_excerpt="me habían diagnosticado con TDA",
    ),
    ProposedFact(
        category="personal",
        fact="La quetiapina le produce efecto sedante notable y le ayuda con bienestar",
        source_excerpt="La quetiapina es una maravilla, desde la primera toma me sentí mejor",
    ),
]


def load_vulnerability_module():
    """Load vulnerability.py without triggering insult.core.__init__ side effects."""
    spec = importlib.util.spec_from_file_location(
        "vuln",
        Path(__file__).parent.parent / "insult" / "core" / "vulnerability.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not locate vulnerability.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch_existing_facts(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    cur = conn.execute(
        "SELECT id, category, fact, updated_at FROM user_facts "
        "WHERE user_id = ? AND deleted_at IS NULL ORDER BY id",
        (user_id,),
    )
    return [{"id": r[0], "category": r[1], "fact": r[2], "updated_at": r[3]} for r in cur]


def find_message_with_excerpt(
    conn: sqlite3.Connection, user_id: str, excerpt: str
) -> tuple[float, str] | None:
    """Return (timestamp, full_message) for the oldest user message containing
    the excerpt verbatim. Substring match avoids float-precision issues that
    break exact-timestamp lookups in SQLite."""
    cur = conn.execute(
        "SELECT timestamp, content FROM messages "
        "WHERE user_id = ? AND role = 'user' AND content LIKE ? "
        "ORDER BY timestamp ASC LIMIT 1",
        (user_id, f"%{excerpt}%"),
    )
    row = cur.fetchone()
    return (row[0], row[1]) if row else None


def main(db_path: Path) -> int:
    if not db_path.exists():
        print(f"ERROR: {db_path} does not exist", file=sys.stderr)
        return 2

    vuln = load_vulnerability_module()
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    existing = fetch_existing_facts(conn, ALEX_USER_ID)
    print(f"=== Alex existing facts in {db_path.name} ({len(existing)} rows) ===")
    for f in existing:
        marker = ""
        score_groups = vuln.matched_signal_groups([{"fact": f["fact"]}])
        if score_groups:
            marker = f"  [matches: {','.join(score_groups)}]"
        print(f"  #{f['id']:>5} [{f['category']:<12}] {f['fact']}{marker}")

    print()
    score_before = vuln.compute_vulnerability_score([{"fact": f["fact"]} for f in existing])
    groups_before = vuln.matched_signal_groups([{"fact": f["fact"]} for f in existing])
    print(f"Score BEFORE restoration: {score_before} (threshold={vuln.VULNERABLE_THRESHOLD}) "
          f"vulnerable={score_before >= vuln.VULNERABLE_THRESHOLD} signals={groups_before}")

    print()
    print("=== Proposed facts (verbatim citations from messages) ===")
    citation_failures: list[ProposedFact] = []
    for pf in PROPOSED_FACTS:
        match = find_message_with_excerpt(conn, ALEX_USER_ID, pf.source_excerpt)
        if match is None:
            citation_failures.append(pf)
            print(f"  [NO MESSAGE WITH EXCERPT] {pf.fact}")
            print(f"    excerpt: {pf.source_excerpt!r}")
            continue
        ts, _msg = match
        score_groups = vuln.matched_signal_groups([{"fact": pf.fact}])
        marker = f"  [matches: {','.join(score_groups)}]" if score_groups else "  [no signal match — context only]"
        print(f"  + [{pf.category:<10}] {pf.fact}{marker}")
        print(f"    source ts={ts}: {pf.source_excerpt!r}")

    if citation_failures:
        print()
        print(f"ERROR: {len(citation_failures)} proposed fact(s) have unverifiable citations.")
        return 3

    print()
    combined = [{"fact": f["fact"]} for f in existing] + [{"fact": pf.fact} for pf in PROPOSED_FACTS]
    score_after = vuln.compute_vulnerability_score(combined)
    groups_after = vuln.matched_signal_groups(combined)
    print(f"Score AFTER restoration: {score_after} (threshold={vuln.VULNERABLE_THRESHOLD}) "
          f"vulnerable={score_after >= vuln.VULNERABLE_THRESHOLD} signals={groups_after}")

    print()
    print("=== SQL that would be executed (NOT RUN) ===")
    print("BEGIN TRANSACTION;")
    for pf in PROPOSED_FACTS:
        sql = (
            "INSERT INTO user_facts (user_id, fact, category, updated_at, source) "
            f"VALUES ('{ALEX_USER_ID}', "
            f"{pf.fact!r}, "
            f"{pf.category!r}, "
            "strftime('%s','now') + 0.0, "
            "'manual');"
        )
        print(f"  {sql}")
    print("COMMIT;")
    print()
    print("To apply: review the SQL above, then run a companion `apply` script "
          "(not yet written — operator approval required first).")

    conn.close()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} /path/to/memory.db", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1])))
