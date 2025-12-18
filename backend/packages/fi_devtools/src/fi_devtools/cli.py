from __future__ import annotations

import typer
from typing import Annotated

from .analysis import (
    analyze_tier1_errors,
    detect_type_errors,
    import_graph,
    inspect_corpus,
    inspect_h5,
    type_check_parsers,
)
from .ci import generate_policy_manifest, verify_policy
from .lint import (
    backend_fix_unused_imports,
    backend_fix_utc_imports,
    fix_broken_type_ignores,
    fix_implicit_string_concat,
    fix_missing_imports,
    fix_status_code_literals,
    fix_type_ignores,
    fix_unused_vars,
    remediate_type_errors,
    remove_unnecessary_type_ignores,
)
from .migrate import migrate_corpus_to_session, migrate_hdf5_to_swmr, migrate_jobs_to_tasks
from .recovery import (
    recover_missing_chunks,
    reprocess_pending,
    transcribe_missing_chunks,
    transcribe_missing_chunks_direct,
)

Args = Annotated[list[str] | None, typer.Argument(help="Extra args forwarded to the script")]

app = typer.Typer(name="fi", help="Free Intelligence DevTools")
lint_app = typer.Typer(name="lint", help="Lint fixers")
migrate_app = typer.Typer(name="migrate", help="Migration tools")
analyze_app = typer.Typer(name="analyze", help="Analysis and inspection")
recover_app = typer.Typer(name="recover", help="Recovery utilities")
ci_app = typer.Typer(name="ci", help="CI helpers")

app.add_typer(lint_app)
app.add_typer(migrate_app)
app.add_typer(analyze_app)
app.add_typer(recover_app)
app.add_typer(ci_app)


# ──────────────────────────────
# LINT
# ──────────────────────────────


@lint_app.command("type-ignores")
def lint_type_ignores(args: Args = None) -> None:
    fix_type_ignores.run(args)


@lint_app.command("unused-vars")
def lint_unused_vars(args: Args = None) -> None:
    fix_unused_vars.run(args)


@lint_app.command("fix-imports")
def lint_fix_imports(args: Args = None) -> None:
    fix_missing_imports.run(args)


@lint_app.command("broken-type-ignores")
def lint_broken_type_ignores(args: Args = None) -> None:
    fix_broken_type_ignores.run(args)


@lint_app.command("status-code-literals")
def lint_status_code_literals(args: Args = None) -> None:
    fix_status_code_literals.run(args)


@lint_app.command("implicit-string-concat")
def lint_implicit_string_concat(args: Args = None) -> None:
    fix_implicit_string_concat.run(args)


@lint_app.command("remove-unused-type-ignores")
def lint_remove_unused_type_ignores(args: Args = None) -> None:
    remove_unnecessary_type_ignores.run(args)


@lint_app.command("remediate-type-errors")
def lint_remediate_type_errors(args: Args = None) -> None:
    remediate_type_errors.run(args)


@lint_app.command("backend-fix-unused-imports")
def lint_backend_fix_unused_imports(args: Args = None) -> None:
    backend_fix_unused_imports.run(args)


@lint_app.command("backend-fix-utc-imports")
def lint_backend_fix_utc_imports(args: Args = None) -> None:
    backend_fix_utc_imports.run(args)


# ──────────────────────────────
# MIGRATE
# ──────────────────────────────


@migrate_app.command("jobs-to-tasks")
def migrate_jobs(args: Args = None) -> None:
    migrate_jobs_to_tasks.run(args)


@migrate_app.command("hdf5-to-swmr")
def migrate_hdf5(args: Args = None) -> None:
    migrate_hdf5_to_swmr.run(args)


@migrate_app.command("corpus-to-session")
def migrate_corpus(args: Args = None) -> None:
    migrate_corpus_to_session.run(args)


# ──────────────────────────────
# ANALYZE
# ──────────────────────────────


@analyze_app.command("import-graph")
def analyze_import_graph(args: Args = None) -> None:
    import_graph.run(args)


@analyze_app.command("inspect-h5")
def analyze_inspect_h5(args: Args = None) -> None:
    inspect_h5.run(args)


@analyze_app.command("type-check-parsers")
def analyze_type_check_parsers(args: Args = None) -> None:
    type_check_parsers.run(args)


@analyze_app.command("detect-type-errors")
def analyze_detect_type_errors(args: Args = None) -> None:
    detect_type_errors.run(args)


@analyze_app.command("inspect-corpus")
def analyze_inspect_corpus(args: Args = None) -> None:
    inspect_corpus.run(args)


@analyze_app.command("tier1-errors")
def analyze_tier1(args: Args = None) -> None:
    analyze_tier1_errors.run(args)


# ──────────────────────────────
# RECOVER
# ──────────────────────────────


@recover_app.command("recover-missing-chunks")
def recover_missing(args: Args = None) -> None:
    recover_missing_chunks.run(args)


@recover_app.command("reprocess-pending")
def recover_reprocess(args: Args = None) -> None:
    reprocess_pending.run(args)


@recover_app.command("transcribe-missing")
def recover_transcribe_missing(args: Args = None) -> None:
    transcribe_missing_chunks.run(args)


@recover_app.command("transcribe-missing-direct")
def recover_transcribe_missing_direct(args: Args = None) -> None:
    transcribe_missing_chunks_direct.run(args)


# ──────────────────────────────
# CI
# ──────────────────────────────


@ci_app.command("verify-policy")
def ci_verify_policy_cmd(args: Args = None) -> None:
    verify_policy.run(args)


@ci_app.command("generate-policy-manifest")
def ci_generate_policy_manifest_cmd(args: Args = None) -> None:
    generate_policy_manifest.run(args)


if __name__ == "__main__":
    app()
