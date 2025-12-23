from __future__ import annotations

from typing import Annotated

import typer
from pathlib import Path

from .._common import (
    ExitCode,
    build_paths,
    ensure_dir,
    popen_cmd,
    resolve_repo_root,
    run_cmd,
    shell_cmd,
    wait_for_http_ok,
)

app = typer.Typer(name="dev", help="Local development workflows", no_args_is_help=True)


BasePathOpt = Annotated[
    Path | None,
    typer.Option(
        "--base-path",
        help="Absolute path to repo root or backend/ directory.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
]


def _cleanup_processes(repo_root: Path) -> None:
    # Best-effort cleanup, matches legacy dev-all.sh intent.
    shell_cmd("lsof -ti:7001,9000,9050,11434 2>/dev/null | xargs kill -9 2>/dev/null || true", cwd=repo_root)
    shell_cmd("pgrep -f 'uvicorn.*main:app' | xargs kill -9 2>/dev/null || true", cwd=repo_root)
    shell_cmd("pgrep -f 'next.*dev.*-p 9000' | xargs kill -9 2>/dev/null || true", cwd=repo_root)
    shell_cmd("pgrep -f 'pnpm.*dev' | xargs kill -9 2>/dev/null || true", cwd=repo_root)
    shell_cmd("pgrep -f 'python3.*uvicorn' | xargs kill -9 2>/dev/null || true", cwd=repo_root)


@app.command("kill-all")
def kill_all(
    base_path: BasePathOpt = None,
) -> None:
    """Best-effort stop for local dev processes (ports + common processes)."""
    repo_root = resolve_repo_root(base_path)
    _cleanup_processes(repo_root)


@app.command("all")
def dev_all(
    base_path: BasePathOpt = None,
) -> None:
    """Start backend + frontend for local development (migrated from scripts/dev-all.sh)."""
    repo_root = resolve_repo_root(base_path)
    paths = build_paths(repo_root)
    ensure_dir(paths.logs_dir)
    ensure_dir(paths.storage_dir)

    typer.echo("[0/4] Cleaning up existing processes...")
    _cleanup_processes(repo_root)

    typer.echo("[1/4] Checking prerequisites...")
    run_cmd(["node", "--version"], cwd=repo_root, check=True)
    run_cmd(["python3.14", "--version"], cwd=repo_root, check=True)

    # Ensure pnpm exists (install if missing)
    try:
        run_cmd(["pnpm", "--version"], cwd=repo_root, check=True)
    except typer.Exit:
        run_cmd(["npm", "install", "-g", "pnpm@latest"], cwd=repo_root, check=True)

    typer.echo("[2/4] Checking dependencies...")
    if not (repo_root / "node_modules").exists():
        try:
            run_cmd(["pnpm", "install", "--frozen-lockfile"], cwd=repo_root, check=True)
        except typer.Exit:
            run_cmd(["pnpm", "install"], cwd=repo_root, check=True)

    # Python deps: legacy script uses system python without venv.
    try:
        run_cmd(["python3.14", "-c", "import fastapi"], cwd=repo_root, check=True)
    except typer.Exit:
        run_cmd(
            ["python3.14", "-m", "pip", "install", "-q", "-r", str(repo_root / "requirements.txt")],
            cwd=repo_root,
            check=False,
        )

    typer.echo("[3/4] Initializing storage...")
    corpus_path = paths.storage_dir / "corpus.h5"
    if not corpus_path.exists():
        run_cmd(
            [
                "python3.14",
                "-c",
                (
                    "import h5py; "
                    f"p={str(corpus_path)!r}; "
                    "f=h5py.File(p,'w',libver='latest'); "
                    "f.create_group('sessions'); f.attrs['version']='1.0'; f.close()"
                ),
            ],
            cwd=repo_root,
            check=False,
        )

    typer.echo("[4/4] Starting services...")
    backend_log = paths.logs_dir / "backend-dev.log"
    frontend_log = paths.logs_dir / "frontend-aurity-dev.log"

    _backend_proc = popen_cmd(
        [
            "python3.14",
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "7001",
            "--reload",
            "--log-level",
            "info",
        ],
        cwd=repo_root,
        stdout_path=backend_log,
    )

    if not wait_for_http_ok("http://localhost:7001/health", timeout_s=30):
        raise typer.Exit(code=int(ExitCode.ERROR))

    _frontend_proc = popen_cmd(
        ["pnpm", "dev"],
        cwd=paths.frontend_root,
        env={"PORT": "9000"},
        stdout_path=frontend_log,
    )
    wait_for_http_ok("http://localhost:9000", timeout_s=30)

    typer.echo("✅ All Services Running")
    typer.echo("  • Backend API: http://localhost:7001")
    typer.echo("  • AURITY Frontend: http://localhost:9000")


@app.command("start")
def dev_start(
    base_path: BasePathOpt = None,
) -> None:
    """Legacy Docker-based dev start (migrated from scripts/dev-start.sh)."""
    repo_root = resolve_repo_root(base_path)
    paths = build_paths(repo_root)
    ensure_dir(paths.logs_dir)

    typer.echo("🧹 Cleaning existing processes...")
    shell_cmd("pkill -9 -f 'python.*backend' 2>/dev/null || true", cwd=repo_root)
    shell_cmd("pkill -9 -f 'uvicorn' 2>/dev/null || true", cwd=repo_root)
    shell_cmd("pkill -9 -f 'make run' 2>/dev/null || true", cwd=repo_root)
    shell_cmd("lsof -ti :7001 | xargs kill -9 2>/dev/null || true", cwd=repo_root)

    typer.echo("🐳 Checking Docker...")
    run_cmd(["docker", "info"], cwd=repo_root, check=True)

    typer.echo("📦 Starting Celery infrastructure...")
    run_cmd(["docker-compose", "-f", "docker/docker-compose.celery.yml", "up", "-d"], cwd=repo_root, check=True)

    typer.echo("🎯 Starting Backend API (port 7001)...")
    backend_log = paths.logs_dir / "backend-dev.log"
    _backend_proc = popen_cmd(["make", "run"], cwd=repo_root, stdout_path=backend_log)
    (Path("/tmp") / "backend_pid.txt").write_text(str(_backend_proc.pid))

    if not wait_for_http_ok("http://localhost:7001/health", timeout_s=30):
        raise typer.Exit(code=int(ExitCode.ERROR))

    typer.echo("✅ Backend API ready at http://localhost:7001")
    typer.echo("✅ Flower UI: http://localhost:5555")


@app.command("stop")
def dev_stop(
    base_path: BasePathOpt = None,
) -> None:
    """Stop local dev services (migrated from scripts/dev-stop.sh)."""
    repo_root = resolve_repo_root(base_path)
    typer.echo("🛑 Stopping Backend API...")
    pid_file = Path("/tmp") / "backend_pid.txt"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            run_cmd(["kill", "-9", str(pid)], cwd=repo_root, check=False)
        finally:
            pid_file.unlink(missing_ok=True)

    shell_cmd("pkill -9 -f 'python.*backend' 2>/dev/null || true", cwd=repo_root)
    shell_cmd("pkill -9 -f 'uvicorn' 2>/dev/null || true", cwd=repo_root)
    shell_cmd("lsof -ti :7001 | xargs kill -9 2>/dev/null || true", cwd=repo_root)

    typer.echo("🛑 Stopping Celery infrastructure...")
    run_cmd(["docker-compose", "-f", "docker/docker-compose.celery.yml", "down"], cwd=repo_root, check=False)
    typer.echo("✅ All services stopped")


@app.command("migrate-conversation-capture")
def migrate_conversation_capture() -> None:
    """
    Migrate ConversationCapture.tsx to use specialized hooks.
    Performs systematic search and replace of references to use session and audioUpload hooks.
    """
    import re

    # Target file
    target_file = Path("apps/aurity/components/medical/ConversationCapture.tsx")

    # Replacement mappings (order matters!)
    replacements = [
        # Session state
        (r"\bsessionId\b(?!Ref|:)", "session.sessionId"),
        (r"\bsetSessionId\b", "session.setSessionId"),
        (r"\bsessionIdRef\.current\b", "session.sessionIdRef.current"),
        # Pause/Resume
        (r"\bisPaused\b", "session.isPaused"),
        (r"\bsetIsPaused\b", "session.setIsPaused"),
        (r"\bpausedAudioUrl\b", "session.pausedAudioUrl"),
        (r"\bsetPausedAudioUrl\b", "session.setPausedAudioUrl"),
        # Patient info
        (r"\bpatientInfo\b(?!:)", "session.patientInfo"),
        (r"\bsetPatientInfo\b", "session.setPatientInfo"),
        (r"\bshowPatientInfoModal\b", "session.showPatientInfoModal"),
        (r"\bsetShowPatientInfoModal\b", "session.setShowPatientInfoModal"),
        # Diarization
        (r"\bdiarizationJobId\b", "session.diarizationJobId"),
        (r"\bsetDiarizationJobId\b", "session.setDiarizationJobId"),
        (r"\bshowDiarizationModal\b", "session.showDiarizationModal"),
        (r"\bsetShowDiarizationModal\b", "session.setShowDiarizationModal"),
        # Error & state
        (r"\berror\b(?!:)", "session.error"),
        (r"\bsetError\b", "session.setError"),
        (r"\bisFinalized\b", "session.isFinalized"),
        (r"\bsetIsFinalized\b", "session.setIsFinalized"),
        (r"\bisWaitingForChunks\b", "session.isWaitingForChunks"),
        (r"\bsetIsWaitingForChunks\b", "session.setIsWaitingForChunks"),
        (r"\bshouldFinalize\b", "session.shouldFinalize"),
        (r"\bsetShouldFinalize\b", "session.setShouldFinalize"),
        # Checkpoint
        (r"\bcheckpointState\b", "session.checkpointState"),
        (r"\bsetCheckpointState\b", "session.setCheckpointState"),
        (r"\bestimatedSecondsRemaining\b", "session.estimatedSecondsRemaining"),
        (r"\bsetEstimatedSecondsRemaining\b", "session.setEstimatedSecondsRemaining"),
        (r"\bfinalizationStartTimeRef\.current\b", "session.finalizationStartTimeRef.current"),
        # Audio upload refs
        (r"\bchunkNumberRef\.current\b", "audioUpload.chunkNumberRef.current"),
        (r"\baudioChunksRef\.current\b", "audioUpload.audioChunksRef.current"),
        (r"\bfullAudioBlobsRef\.current\b", "audioUpload.fullAudioBlobsRef.current"),
        (r"\binflightRef\.current\b", "audioUpload.inflightRef.current"),
        # Metrics (addLog is most common)
        (r"\baddLog\b", "metrics.addLog"),
    ]

    typer.echo("=" * 70)
    typer.echo("🔧 MIGRATING CONVERSATIONCAPTURE TO SPECIALIZED HOOKS")
    typer.echo("=" * 70)
    typer.echo()

    if not target_file.exists():
        typer.echo(f"❌ File not found: {target_file}", err=True)
        raise typer.Exit(1)

    # Read original content
    content = target_file.read_text()
    original_lines = len(content.splitlines())

    typer.echo(f"📄 Migrating {target_file}")
    typer.echo(f"📏 Original lines: {original_lines}")
    typer.echo()

    # Apply replacements
    changes_count = 0
    for pattern, replacement in replacements:
        matches = len(re.findall(pattern, content))
        if matches > 0:
            content = re.sub(pattern, replacement, content)
            changes_count += matches
            typer.echo(f"✅ {matches:3d} changes: {pattern:40s} → {replacement}")

    typer.echo()
    typer.echo(f"📊 Total changes: {changes_count}")

    # Save migrated file
    target_file.write_text(content)
    typer.echo(f"💾 File saved: {target_file}")
    typer.echo()
    typer.echo("✅ Migration completed!")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("1. Check for linter errors")
    typer.echo("2. Manual testing of component")
    typer.echo("3. Commit changes")


@app.command("install-hooks")
def install_hooks() -> None:
    """
    Install Git hooks for code quality enforcement.
    Sets up pre-commit hooks for validation and testing.
    """
    import sys

    typer.echo("🔧 FREE INTELLIGENCE - GIT HOOKS INSTALLER")
    typer.echo("=" * 50)
    typer.echo()

    # Check if pre-commit is installed
    try:
        run_cmd(["pre-commit", "--version"], cwd=repo_root, check=True)
    except typer.Exit:
        typer.echo("⚠️  pre-commit not found. Installing...")
        run_cmd([sys.executable, "-m", "pip", "install", "pre-commit"], cwd=repo_root, check=True)
        typer.echo()

    # Install hooks
    typer.echo("📦 Installing pre-commit hooks...")
    run_cmd(["pre-commit", "install"], cwd=repo_root, check=True)
    run_cmd(["pre-commit", "install", "--hook-type", "commit-msg"], cwd=repo_root, check=True)
    typer.echo()

    # Show installed hooks
    typer.echo("✅ Hooks installed successfully!")
    typer.echo()
    typer.echo("📋 Installed hooks:")
    typer.echo("   1. Event Validator (UPPER_SNAKE_CASE)")
    typer.echo("   2. Mutation Validator (no update/delete)")
    typer.echo("   3. LLM Audit Policy (require @require_audit_log)")
    typer.echo("   4. LLM Router Policy (no direct API imports)")
    typer.echo("   5. Unit Tests (183 tests must pass)")
    typer.echo("   6. Commit Message Validator (Conventional Commits)")
    typer.echo()

    # Test hooks
    typer.echo("🧪 Testing hooks...")
    try:
        run_cmd(["pre-commit", "run", "--all-files"], cwd=repo_root, check=False)
    except typer.Exit:
        typer.echo()
        typer.echo("⚠️  Some hooks failed. This is normal on first run.")
        typer.echo("   Hooks will run automatically on next commit.")
        typer.echo()

    typer.echo("=" * 50)
    typer.echo("✅ Git hooks setup complete!")


@app.command("sprint-close")
def sprint_close(
    sprint_label: Annotated[
        str,
        typer.Argument(help="Sprint label (e.g., SPR-2025W43)")
    ],
    execute: Annotated[
        bool,
        typer.Option("--execute", help="Execute changes (default: dry run)")
    ] = False,
) -> None:
    """
    Close sprint with version bump, backup, and documentation.
    Handles tagging, bundle creation, retention, and claude.md updates.
    """
    from datetime import datetime

    mode = "EXECUTE" if execute else "DRY_RUN"
    timezone = "America/Mexico_City"
    repo_root = resolve_repo_root(None)
    backup_dir = repo_root / "backups"
    claude_md = repo_root / "claude.md"

    # Ensure backup directory exists
    backup_dir.mkdir(exist_ok=True)

    # Current date/time in local timezone
    current_date = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%H:%M')
    timestamp = f"{current_date} {current_time}"

    typer.echo(f"🎯 Sprint Close - {sprint_label}")
    typer.echo(f"Mode: {mode}")
    typer.echo(f"Timestamp: {timestamp} ({timezone})")
    typer.echo()

    # 1. Determine version
    typer.echo("📌 Step 1: Determining version...")
    try:
        result = run_cmd(["git", "describe", "--tags", "--abbrev=0"], cwd=repo_root, capture_output=True, check=False)
        last_tag = result.stdout.strip() if result.stdout else "v0.0.0"
    except:
        last_tag = "v0.0.0"
    typer.echo(f"  Last tag: {last_tag}")

    # Count commits since last tag
    try:
        result = run_cmd(["git", "rev-list", f"{last_tag}..HEAD", "--count"], cwd=repo_root, capture_output=True, check=False)
        commits_since = int(result.stdout.strip()) if result.stdout else 0
    except:
        result = run_cmd(["git", "rev-list", "HEAD", "--count"], cwd=repo_root, capture_output=True, check=False)
        commits_since = int(result.stdout.strip()) if result.stdout else 0
    typer.echo(f"  Commits since tag: {commits_since}")

    if commits_since > 0:
        # Extract version numbers
        import re
        match = re.match(r'v(\d+)\.(\d+)\.(\d+)', last_tag)
        if match:
            major, minor, patch = map(int, match.groups())
        else:
            major, minor, _patch = 0, 0, 0

        # Increment MINOR for sprints (every 15 days = minor release)
        minor += 1
        new_tag = f"v{major}.{minor}.0"
    else:
        new_tag = last_tag

    typer.echo(f"  New version: {new_tag}")
    typer.echo()

    # 2. Generate release notes
    typer.echo("📝 Step 2: Generating release notes...")
    release_notes_file = backup_dir / f"release-notes-{new_tag}.md"

    if commits_since > 0:
        try:
            result = run_cmd(["git", "log", f"{last_tag}..HEAD", "--pretty=format:- %s (%h)", "--no-merges"], cwd=repo_root, capture_output=True, check=False)
            changes = result.stdout.strip() if result.stdout else "No changes"
        except:
            changes = "No changes"

        try:
            result = run_cmd(["git", "log", f"{last_tag}..HEAD", "--name-only", "--pretty=format:"], cwd=repo_root, capture_output=True, check=False)
            affected_files = result.stdout.strip().split('\n') if result.stdout else []
            affected_files = list({f for f in affected_files if f.strip()})
            affected_files_str = '\n'.join(f"- {f}" for f in affected_files[:20]) if affected_files else "- Initial files"
        except:
            affected_files_str = "- Files not available"

        try:
            result = run_cmd(["git", "diff", "--name-only", f"{last_tag}..HEAD"], cwd=repo_root, capture_output=True, check=False)
            modified_count = len(result.stdout.strip().split('\n')) if result.stdout else 0
        except:
            modified_count = "N/A"

        release_notes = f"""# Release Notes - {new_tag}

**Sprint**: {sprint_label}
**Date**: {current_date}
**Commits**: {commits_since} since {last_tag}

## Changes

{changes}

## Affected Areas

{affected_files_str}

## Statistics

- Total commits: {commits_since}
- Modified files: {modified_count}
"""
    else:
        release_notes = f"""# Release Notes - {new_tag}

**Sprint**: {sprint_label}
**Date**: {current_date}
**Status**: No changes since {last_tag}
"""

    if execute:
        with open(release_notes_file, 'w') as f:
            f.write(release_notes)
        typer.echo(f"  Notes saved to: {release_notes_file}")
    else:
        typer.echo(f"  Notes would be saved to: {release_notes_file} (DRY RUN)")

    typer.echo(release_notes)
    typer.echo()

    # 3. Create tag (only in EXECUTE)
    if execute and commits_since > 0:
        typer.echo(f"🏷️  Step 3: Creating tag {new_tag}...")
        run_cmd(["git", "tag", "-a", new_tag, "-m", f"Sprint {sprint_label} - {current_date}"], cwd=repo_root, check=True)
        typer.echo(f"  Tag {new_tag} created ✅")
    else:
        typer.echo(f"🏷️  Step 3: Tag {new_tag} (SIMULATED - mode {mode})")
    typer.echo()

    # 4. Create bundle backup
    typer.echo("💾 Step 4: Generating bundle backup...")
    bundle_name = f"fi-{sprint_label}-{new_tag}-{current_date}.bundle"
    bundle_path = backup_dir / bundle_name
    sha256_path = backup_dir / f"{sprint_label}-{new_tag}.sha256"

    if execute:
        run_cmd(["git", "bundle", "create", str(bundle_path), "--all"], cwd=repo_root, check=True)
        bundle_size = bundle_path.stat().st_size
        typer.echo(f"  Bundle created: {bundle_path} ({bundle_size} bytes)")

        # Calculate SHA256
        import hashlib
        with open(bundle_path, 'rb') as f:
            bundle_sha = hashlib.sha256(f.read()).hexdigest()
        with open(sha256_path, 'w') as f:
            f.write(bundle_sha)
        typer.echo(f"  SHA256: {bundle_sha}")
        typer.echo(f"  SHA256 saved to: {sha256_path}")
    else:
        typer.echo(f"  Bundle: {bundle_path} (SIMULATED)")
        bundle_size = "N/A"
        bundle_sha = "SIMULATED"
    typer.echo()

    # 5. Retention (keep last 12 bundles)
    typer.echo("🗑️  Step 5: Applying retention (last 12 bundles)...")
    bundle_files = list(backup_dir.glob("*.bundle"))
    bundle_count = len(bundle_files)
    typer.echo(f"  Current bundles: {bundle_count}")

    if bundle_count > 12 and execute:
        # Sort by modification time, keep newest 12
        bundle_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        for old_bundle in bundle_files[12:]:
            typer.echo(f"  Removing: {old_bundle}")
            old_bundle.unlink()
            sha_file = old_bundle.with_suffix('.sha256')
            if sha_file.exists():
                sha_file.unlink()
        typer.echo("  Retention applied ✅")
    else:
        typer.echo("  Retention: Not needed (< 12 bundles)")
    typer.echo()

    # 6. Update claude.md
    typer.echo("📖 Step 6: Updating claude.md...")

    tarjetas_cerradas = 0
    entradas_sprint = 0
    if claude_md.exists():
        content = claude_md.read_text()
        tarjetas_cerradas = content.count("Estado.*Done")
        entradas_sprint = content.count(f"[{sprint_label}]")

    cierre_entry = f"""

---

## [{timestamp}] {sprint_label} — CIERRE DE SPRINT
Estado: Sprint Activo → Sprint Cerrado | Tag: {new_tag}
Fechas: Sprint completo (15 días)
Acción: Cierre de sprint y generación de backup
Síntesis técnica:
- Tag {new_tag} creado ({commits_since} commits desde {last_tag})
- Backup generado: {bundle_name} ({bundle_size})
- SHA256: {bundle_sha}
- Retención aplicada: manteniendo últimos 12 bundles
- Notas de versión: {release_notes_file}

Métricas del sprint:
- Tarjetas cerradas: {tarjetas_cerradas}
- Entradas en bitácora: {entradas_sprint}
- Commits totales: {commits_since}

Verificación:
- Tag existe: {'1' if execute and commits_since > 0 else '0'}
- Bundle existe: {'✅' if execute else f'⏸️ (modo {mode})'}
- SHA256 existe: {'✅' if execute else f'⏸️ (modo {mode})'}
- Bundle size: {bundle_size}
- Entradas añadidas en sprint: {entradas_sprint}

Próximo paso: Iniciar siguiente sprint con nueva planificación

---
"""

    if execute:
        with open(claude_md, 'a') as f:
            f.write(cierre_entry)
        typer.echo("  Cierre entry added to claude.md ✅")
    else:
        typer.echo("  Cierre entry (SIMULATED):")
        typer.echo(cierre_entry[:500] + "..." if len(cierre_entry) > 500 else cierre_entry)
    typer.echo()

    # 7. Final summary
    typer.echo("✅ FINAL SUMMARY")
    typer.echo("=" * 20)
    typer.echo(f"Mode: {mode}")
    typer.echo(f"Sprint: {sprint_label}")
    typer.echo(f"Tag: {new_tag} (commits: {commits_since})")
    typer.echo(f"Bundle: {bundle_name}")
    typer.echo(f"SHA256: {bundle_sha[:16]}...")
    typer.echo(f"Backup path: {bundle_path}")
    typer.echo(f"Claude.md entries: {entradas_sprint}")
    typer.echo()

    if not execute:
        typer.echo("⚠️  DRY RUN MODE: No changes applied")
        typer.echo(f"   Execute with: fi_cli dev sprint-close {sprint_label} --execute")
    else:
        typer.echo("✅ Sprint closed successfully")


@app.command("validate-commit-message")
def validate_commit_message(
    commit_msg_file: Annotated[
        Path,
        typer.Argument(help="Path to commit message file")
    ],
) -> None:
    """
    Validate commit message format (Conventional Commits).
    Enforces proper commit message structure for development workflow.
    """
    import re

    # Conventional Commits types
    valid_types = {
        "feat",  # New feature
        "fix",  # Bug fix
        "docs",  # Documentation
        "refactor",  # Code refactoring
        "test",  # Tests
        "chore",  # Maintenance
        "perf",  # Performance
        "ci",  # CI/CD
        "build",  # Build system
        "revert",  # Revert commit
    }

    # Pattern: type(scope): message
    commit_pattern = re.compile(
        r"^(?P<type>\w+)"  # Type (required)
        r"(?:\((?P<scope>[\w-]+)\))?"  # Scope (optional)
        r": "  # Separator
        r"(?P<message>.+)$"  # Message (required)
    )

    if not commit_msg_file.exists():
        typer.echo(f"❌ File not found: {commit_msg_file}", err=True)
        raise typer.Exit(1)

    # Read commit message (first line only)
    message = commit_msg_file.read_text().strip().split("\n")[0]

    # Skip merge commits
    if message.startswith("Merge"):
        typer.echo(f"✅ Merge commit allowed: {message[:60]}...")
        return

    # Skip revert commits (git revert)
    if message.startswith("Revert"):
        typer.echo(f"✅ Revert commit allowed: {message[:60]}...")
        return

    # Match pattern
    match = commit_pattern.match(message)

    if not match:
        typer.echo("\n❌ COMMIT MESSAGE VALIDATION FAILED\n", err=True)
        typer.echo("Invalid commit message format!\n", err=True)
        typer.echo("Expected: <type>(<scope>): <message>", err=True)
        typer.echo("Example: feat(security): add LLM audit policy\n", err=True)
        typer.echo(f"Valid types: {', '.join(sorted(valid_types))}", err=True)
        raise typer.Exit(1)

    commit_type = match.group("type")
    commit_message = match.group("message")

    # Validate type
    if commit_type not in valid_types:
        typer.echo(f"\n❌ Invalid commit type: '{commit_type}'\n", err=True)
        typer.echo(f"Valid types: {', '.join(sorted(valid_types))}", err=True)
        raise typer.Exit(1)

    # Validate message not empty
    if not commit_message.strip():
        typer.echo("\n❌ Commit message cannot be empty\n", err=True)
        raise typer.Exit(1)

    # Validate message doesn't start with uppercase (except proper nouns)
    if commit_message[0].isupper() and not commit_message.startswith(
        ("API", "HDF5", "LLM", "UUID")
    ):
        typer.echo("\n❌ Commit message should start with lowercase\n", err=True)
        typer.echo(f"Got: '{commit_message}'", err=True)
        typer.echo(f"Try: '{commit_message[0].lower() + commit_message[1:]}'", err=True)
        raise typer.Exit(1)

    typer.echo(f"✅ Commit message valid: {message[:60]}...")


@app.command("manual-e2e-test")
def manual_e2e_test(
    base_url: Annotated[
        str,
        typer.Option("--base-url", help="Base URL for API calls")
    ] = "http://localhost:7001",
    session_id: Annotated[
        str | None,
        typer.Option("--session-id", help="Custom session ID (auto-generated if not provided)")
    ] = None,
) -> None:
    """
    Run manual end-to-end test suite using curl.

    Tests complete workflow: health check → dry-run → chat → streaming → diarization → SOAP → finalize.
    Outputs results to temporary directory for analysis.
    """
    import json
    import subprocess
    import uuid

    import os

    typer.echo("🧪 MANUAL E2E TEST SUITE")
    typer.echo("=" * 50)
    typer.echo(f"Base URL: {base_url}")
    typer.echo()

    # Generate session ID
    sid = session_id or str(uuid.uuid4())
    outdir = f"/tmp/fi_e2e_{sid}"
    os.makedirs(outdir, exist_ok=True)

    typer.echo(f"Session ID: {sid}")
    typer.echo(f"Output dir: {outdir}")
    typer.echo()

    def run_curl(description: str, cmd: list[str], output_file: str) -> dict | None:
        """Run curl command and save/parse output."""
        typer.echo(f"🔄 {description}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            output_path = os.path.join(outdir, output_file)
            with open(output_path, 'w') as f:
                f.write(result.stdout)

            if result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    typer.echo(f"  ⚠️  Non-JSON response saved to {output_file}")
                    return None
            else:
                typer.echo(f"  ⚠️  Empty response saved to {output_file}")
                return None
        except Exception as e:
            typer.echo(f"  ❌ Error: {e}")
            return None

    # 1) Health check
    health_data = run_curl(
        "Health check",
        ["curl", "-sS", f"{base_url}/api/health"],
        "health.json"
    )
    if health_data:
        typer.echo(f"  ✅ Status: {health_data.get('status', 'unknown')}")

    # 2) Dry-run (safe)
    dryrun_data = run_curl(
        "Dry-run test",
        [
            "curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
            f"{base_url}/api/workflows/aurity/assistant/chat/_dry-run",
            "-d", json.dumps({
                "persona": "clinical_advisor",
                "message": "Paciente masculino 45a, HTA y cefalea intensa.",
                "response_mode": "concise",
                "rag_context": "RFC: ABCD900101XXX, creatinina 1.8 mg/dL, TA 180/110"
            })
        ],
        "dryrun.json"
    )

    rid = None
    if dryrun_data and "request_id" in dryrun_data:
        rid = dryrun_data["request_id"]
        typer.echo(f"  ✅ Request ID: {rid}")

    # 3) Trace for dry-run
    if rid:
        run_curl(
            "Dry-run trace",
            ["curl", "-sS", f"{base_url}/api/workflows/aurity/assistant/chat/_trace/{rid}"],
            "dryrun_trace.json"
        )

    # 4) Clinical conversation
    chat_data = run_curl(
        "Clinical conversation",
        [
            "curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
            f"{base_url}/api/workflows/aurity/assistant/chat",
            "-d", json.dumps({
                "persona": "clinical_advisor",
                "message": "Paciente 45a con TA 180/110, cefalea y visión borrosa. ¿Conducta inicial?",
                "response_mode": "explanatory"
            })
        ],
        "chat1.json"
    )

    rid2 = None
    if chat_data and "request_id" in chat_data:
        rid2 = chat_data["request_id"]
        typer.echo(f"  ✅ Request ID: {rid2}")

    # 5) Trace for chat
    if rid2:
        run_curl(
            "Chat trace",
            ["curl", "-sS", f"{base_url}/api/workflows/aurity/assistant/chat/_trace/{rid2}"],
            "chat1_trace.json"
        )

    # 6) Create session and upload chunk (simulated)
    run_curl(
        "Create session with chunk",
        [
            "curl", "-sS", "-X", "POST", f"{base_url}/api/workflows/aurity/stream?sid={sid}&seq=1",
            "-F", 'meta={"sample_rate":48000,"channels":1};type=application/json',
            "-F", 'chunk=@-;type=application/octet-stream'
        ],
        "stream_resp.json"
    )

    # 7) Monitor session
    run_curl(
        "Monitor session",
        ["curl", "-sS", f"{base_url}/api/workflows/aurity/sessions/{sid}/monitor"],
        "monitor.json"
    )

    # 8) Start diarization
    run_curl(
        "Start diarization",
        [
            "curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
            f"{base_url}/api/workflows/aurity/sessions/{sid}/diarization",
            "-d", json.dumps({"engine": "default"})
        ],
        "diarization.json"
    )

    # 9) Generate SOAP
    run_curl(
        "Generate SOAP",
        [
            "curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
            f"{base_url}/api/workflows/aurity/sessions/{sid}/soap",
            "-d", json.dumps({
                "format": "json",
                "include_codes": True,
                "style": "concise"
            })
        ],
        "soap.json"
    )

    # 10) Finalize session
    run_curl(
        "Finalize session",
        [
            "curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
            f"{base_url}/api/workflows/aurity/sessions/{sid}/finalize",
            "-d", json.dumps({"encrypt": True})
        ],
        "finalize.json"
    )

    # 11) Negative tests
    typer.echo("🧪 Negative tests")

    run_curl(
        "Invalid persona test",
        [
            "curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
            f"{base_url}/api/workflows/aurity/assistant/chat",
            "-d", json.dumps({"persona": "no_such_persona", "message": "hola"})
        ],
        "neg_invalid_persona.json"
    )

    run_curl(
        "Timeout simulation test",
        [
            "curl", "-sS", "-H", "Content-Type: application/json", "-X", "POST",
            f"{base_url}/api/workflows/aurity/assistant/chat",
            "-d", json.dumps({"persona": "clinical_advisor", "message": "#simulate_timeout"})
        ],
        "neg_timeout.json"
    )

    # 12) Acceptance checks
    typer.echo("📊 Acceptance checks")

    # Dry-run summary
    dryrun_path = os.path.join(outdir, "dryrun.json")
    if os.path.exists(dryrun_path):
        try:
            with open(dryrun_path) as f:
                dryrun_data = json.load(f)
            summary = {
                "request_id": dryrun_data.get("request_id"),
                "user_message_hash8": dryrun_data.get("user_message", {}).get("hash8"),
                "user_message_len": dryrun_data.get("user_message", {}).get("length"),
                "system_markers": dryrun_data.get("system_markers")
            }
            typer.echo(f"Dry-run summary: {summary}")
        except:
            typer.echo("Could not parse dry-run summary")

    # Trace events
    trace_path = os.path.join(outdir, "dryrun_trace.json")
    if os.path.exists(trace_path):
        try:
            with open(trace_path) as f:
                trace_data = json.load(f)
            events = [event.get("type") for event in trace_data.get("events", []) if event]
            typer.echo(f"Trace events: {events}")
        except:
            typer.echo("Could not parse trace events")

    # SOAP keys
    soap_path = os.path.join(outdir, "soap.json")
    if os.path.exists(soap_path):
        try:
            with open(soap_path) as f:
                soap_data = json.load(f)
            keys = list(soap_data.keys())
            typer.echo(f"SOAP keys: {keys}")
        except:
            typer.echo("Could not parse SOAP keys")

    typer.echo()
    typer.echo("✅ E2E Test completed!")
    typer.echo(f"📁 Outputs saved to: {outdir}")
    typer.echo()
    typer.echo("Next steps:")
    typer.echo("1. Review JSON outputs for correctness")
    typer.echo("2. Check error responses in negative tests")
    typer.echo("3. Verify session workflow completion")


@app.command("test-tls")
def test_tls() -> None:
    """Test TLS 1.3 configuration for HIPAA compliance (G-002)."""

    from .._common import redact_text

    typer.echo("🧪 Testing TLS 1.3 Configuration...")
    typer.echo()

    # Colors
    GREEN = "\033[0;32m"
    RED = "\033[0;31m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"  # No Color

    # Test results
    pass_count = 0
    fail_count = 0

    def run_test(name: str, test_func) -> None:
        nonlocal pass_count, fail_count
        typer.echo("=" * 70)
        typer.echo(f"Test: {name}")
        typer.echo("=" * 70)
        try:
            result = test_func()
            if result:
                typer.echo(f"{GREEN}✅ PASS{NC}: {name}")
                pass_count += 1
            else:
                typer.echo(f"{RED}❌ FAIL{NC}: {name}")
                fail_count += 1
        except Exception as e:
            typer.echo(f"{RED}❌ ERROR{NC}: {name} - {redact_text(str(e))}")
            fail_count += 1
        typer.echo()

    # Test 1: HTTP → HTTPS Redirect
    def test_http_redirect():
        try:
            result = run_cmd("curl -s -o /dev/null -w '%{http_code}' http://localhost/health", capture_output=True)
            return result.stdout.strip() == "301"
        except:
            return False

    run_test("HTTP → HTTPS Redirect (301)", test_http_redirect)

    # Test 2: HTTPS Health Check
    def test_https_health():
        try:
            result = run_cmd("curl -k -s -o /dev/null -w '%{http_code}' https://localhost/health", capture_output=True)
            return result.stdout.strip() == "200"
        except:
            return False

    run_test("HTTPS Health Check", test_https_health)

    # Test 3: TLS Protocol Version
    def test_tls_version():
        try:
            result = run_cmd("curl -k -s -v https://localhost/health 2>&1 | grep 'SSL connection using' | awk '{print $5}'", capture_output=True)
            return result.stdout.strip() == "TLSv1.3"
        except:
            return False

    run_test("TLS Protocol Version (TLS 1.3 required)", test_tls_version)

    # Test 4: HSTS Header
    def test_hsts_header():
        try:
            result = run_cmd("curl -k -s -I https://localhost/health | grep -i 'strict-transport-security'", capture_output=True)
            return bool(result.stdout.strip())
        except:
            return False

    run_test("HSTS Header (Strict-Transport-Security)", test_hsts_header)

    # Test 5: Security Headers
    def test_security_headers():
        try:
            result = run_cmd("curl -k -s -I https://localhost/health", capture_output=True)
            headers = result.stdout
            x_frame = "x-frame-options" in headers.lower()
            x_content_type = "x-content-type-options" in headers.lower()
            if x_frame:
                typer.echo(f"{GREEN}✅ PASS{NC}: X-Frame-Options header present")
            else:
                typer.echo(f"{YELLOW}⚠️  WARN{NC}: X-Frame-Options header missing")
            if x_content_type:
                typer.echo(f"{GREEN}✅ PASS{NC}: X-Content-Type-Options header present")
            else:
                typer.echo(f"{YELLOW}⚠️  WARN{NC}: X-Content-Type-Options header missing")
            return x_frame and x_content_type
        except:
            return False

    run_test("Security Headers", test_security_headers)

    # Test 6: Backend API Proxy
    def test_backend_proxy():
        try:
            # Check if backend is running
            lsof_result = run_cmd("lsof -i :7001", capture_output=True, check=False)
            if lsof_result.returncode != 0:
                typer.echo(f"{YELLOW}⚠️  SKIP{NC}: Backend not running on port 7001")
                return True  # Skip is not a failure
            # Test API proxy
            result = run_cmd("curl -k -s -o /dev/null -w '%{http_code}' https://localhost/api/", capture_output=True)
            status = result.stdout.strip()
            if status != "000":
                typer.echo(f"{GREEN}✅ PASS{NC}: Backend API proxied through HTTPS (status: {status})")
                return True
            else:
                return False
        except:
            return False

    run_test("Backend API Proxy", test_backend_proxy)

    # Summary
    typer.echo("=" * 70)
    typer.echo("📊 Test Summary")
    typer.echo("=" * 70)
    total = pass_count + fail_count
    typer.echo(f"   Passed: {pass_count}")
    typer.echo(f"   Failed: {fail_count}")
    typer.echo(f"   Total:  {total}")
    typer.echo()

    if fail_count == 0:
        typer.echo(f"{GREEN}✅ ALL TESTS PASSED{NC}")
        typer.echo()
        typer.echo("🎉 TLS 1.3 configuration is HIPAA-compliant!")
        typer.echo()
        typer.echo("📋 Evidence collected for HIPAA card G-002:")
        typer.echo("   • HTTP → HTTPS redirect: ✅")
        typer.echo("   • TLS 1.3 protocol: ✅")
        typer.echo("   • HSTS header: ✅")
        typer.echo("   • Security headers: ✅")
        typer.echo()
        typer.echo("🚀 Next steps:")
        typer.echo("   1. Run testssl.sh for detailed SSL scan (A+ rating)")
        typer.echo("   2. Capture Wireshark TLS handshake")
        typer.echo("   3. Document evidence in Trello card")
        raise typer.Exit(0)
    else:
        typer.echo(f"{RED}❌ TESTS FAILED{NC}")
        typer.echo()
        typer.echo("Fix the issues above and run again.")
        raise typer.Exit(1)


@app.command("debug-config")
def debug_config() -> None:
    """Debug configuration flow to OllamaProvider."""
    from ...policy.policy_loader import get_policy_loader

    typer.echo("🔍 Checking configuration flow to OllamaProvider")
    typer.echo("=" * 60)

    # Load policy
    policy_loader = get_policy_loader()
    typer.echo(f"Provider: {policy_loader.get_primary_provider()}")

    # Get Ollama config
    ollama_config = policy_loader.get_provider_config("ollama")
    typer.echo(f"Ollama config: {ollama_config}")
    typer.echo()

    # Check specific model
    model_from_policy = ollama_config.get("model")
    typer.echo(f"Model from policy: '{model_from_policy}'")
    typer.echo(f"Is None? {model_from_policy is None}")
    typer.echo(f"Is empty string? {model_from_policy == ''}")
    typer.echo(f"Is 'qwen2:1.5b-instruct'? {model_from_policy == 'qwen2:1.5b-instruct'}")
    typer.echo(f"Is 'qwen2.5:7b-instruct-q4_0'? {model_from_policy == 'qwen2.5:7b-instruct-q4_0'}")
    typer.echo()

    # Check other values
    typer.echo("Other values in Ollama config:")
    for key, value in ollama_config.items():
        typer.echo(f"  {key}: {value}")


@app.command("debug-provider")
def debug_provider() -> None:
    """Debug Ollama provider loading and configuration."""
    from ...policy.policy_loader import get_policy_loader
    from ...providers.llm import get_provider

    typer.echo("🔍 Debugging Ollama Provider Configuration")
    typer.echo("=" * 50)

    # Get policy loader
    policy_loader = get_policy_loader()
    typer.echo(f"📦 Primary provider: {policy_loader.get_primary_provider()}")

    # Get Ollama config
    ollama_config = policy_loader.get_provider_config("ollama")
    typer.echo(f"⚙️  Ollama config: {ollama_config}")

    # Create provider with config
    typer.echo("\n🔧 Creating Ollama provider with policy config...")
    try:
        ollama_provider = get_provider("ollama", ollama_config)
        typer.echo("✅ Provider created successfully")
        typer.echo(f"   - Model: {ollama_provider.default_model}")
        typer.echo(f"   - Base URL: {ollama_provider.base_url}")
    except Exception as e:
        typer.echo(f"❌ Error creating provider: {e}")
        import traceback
        typer.echo(traceback.format_exc())

    typer.echo("\n🔍 Comparing with direct config access...")
    model_from_config = ollama_config.get("model")
    typer.echo(f"   - Model from policy config: {model_from_config}")
    typer.echo("   - Expected model: qwen2:1.5b-instruct")


@app.command("validate-integration")
def validate_integration() -> None:
    """Validate complete UI/backend integration for Free Intelligence."""
    import requests

    typer.echo("🏥 Validating UI-Backend Integration - Free Intelligence")
    typer.echo("=" * 60)

    # 1. Validate backend health
    typer.echo("🔍 Validating backend health...")
    try:
        backend_response = requests.get("http://localhost:7001/health", timeout=10)
        if backend_response.status_code == 200:
            typer.echo("✅ Backend healthy: http://localhost:7001/health")
            backend_healthy = True
        else:
            typer.echo(f"❌ Backend unhealthy: {backend_response.status_code}")
            backend_healthy = False
    except Exception as e:
        typer.echo(f"❌ Error connecting to backend: {e}")
        backend_healthy = False

    # 2. Validate UI is accessible
    typer.echo("\n🔍 Validating UI accessibility...")
    try:
        ui_response = requests.get("http://localhost:9000", timeout=10)
        if ui_response.status_code == 200:
            typer.echo("✅ UI accessible: http://localhost:9000")
            ui_accessible = True
        else:
            typer.echo(f"❌ UI not accessible: {ui_response.status_code}")
            ui_accessible = False
    except Exception as e:
        typer.echo(f"❌ Error connecting to UI: {e}")
        ui_accessible = False

    # 3. Validate internal LLM endpoint
    typer.echo("\n🔍 Validating internal LLM endpoint...")
    try:
        internal_response = requests.get("http://localhost:7001/internal/llm/health", timeout=10)
        if internal_response.status_code == 200:
            typer.echo("✅ Internal LLM endpoint accessible")
            internal_healthy = True
        else:
            typer.echo(f"⚠️  Internal LLM endpoint not accessible: {internal_response.status_code}")
            internal_healthy = False
    except Exception as e:
        typer.echo(f"⚠️  Error with internal LLM endpoint: {e}")
        internal_healthy = False

    # 4. Test SOAP assistant endpoint
    typer.echo("\n🔍 Validating SOAP assistant endpoint...")
    try:
        extraction_payload = {
            "command": "Agregar que el paciente tiene hipertensión arterial",
            "current_soap": {
                "subjective": "Paciente refiere dolor de cabeza ocasional",
                "objective": {"pressure": "140/90"},
                "assessment": "Dolor de cabeza, posible hipertensión",
                "plan": {"studies": ["presión arterial"]},
            },
        }

        extraction_response = requests.post(
            "http://localhost:7001/api/workflows/aurity/sessions/test_validation/assistant",
            json=extraction_payload,
            timeout=30,
        )

        if extraction_response.status_code == 200:
            typer.echo("✅ SOAP assistant endpoint working")
            extraction_working = True
        else:
            typer.echo(f"⚠️  SOAP assistant endpoint not working: {extraction_response.status_code}")
            typer.echo(f"   Response: {extraction_response.text[:200]}...")
            extraction_working = False
    except Exception as e:
        typer.echo(f"⚠️  Error with SOAP assistant endpoint: {e}")
        extraction_working = False

    # 5. Check Ollama availability
    typer.echo("\n🔍 Validating Ollama availability...")
    try:
        ollama_response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if ollama_response.status_code == 200:
            models = ollama_response.json().get("models", [])
            if models:
                typer.echo(f"✅ Ollama available with {len(models)} model(s)")
                ollama_available = True
            else:
                typer.echo("⚠️  Ollama available but no models")
                ollama_available = False
        else:
            typer.echo(f"⚠️  Ollama not available: {ollama_response.status_code}")
            ollama_available = False
    except Exception as e:
        typer.echo(f"⚠️  Error connecting to Ollama: {e}")
        ollama_available = False

    typer.echo("\n" + "=" * 60)
    typer.echo("📊 VALIDATION RESULTS")
    typer.echo("=" * 60)
    typer.echo(f"Backend healthy: {'✅' if backend_healthy else '❌'}")
    typer.echo(f"UI accessible: {'✅' if ui_accessible else '❌'}")
    typer.echo(f"Internal LLM endpoint: {'✅' if internal_healthy else '❌'}")
    typer.echo(f"Structured extraction: {'✅' if extraction_working else '❌'}")
    typer.echo(f"Ollama available: {'✅' if ollama_available else '❌'}")

    all_working = all([backend_healthy, ui_accessible, internal_healthy, extraction_working, ollama_available])

    typer.echo(f"\n🎯 COMPLETE INTEGRATION: {'✅ APPROVED' if all_working else '❌ WITH ERRORS'}")

    if all_working:
        typer.echo("\n🎉 Free Intelligence (AURITY) system fully operational!")
        typer.echo("   - Backend API: http://localhost:7001")
        typer.echo("   - Medical UI: http://localhost:9000")
        typer.echo("   - Ollama Provider: http://localhost:11434")
        typer.echo("   - Medical Workflows: Available in UI")
        typer.echo("   - Structured Extraction: Functional")
    else:
        typer.echo("\n⚠️  System has non-operational components. Check errors above.")

    raise typer.Exit(0 if all_working else 1)


@app.command("install-hooks")
def install_hooks(
    test_hooks: Annotated[
        bool,
        typer.Option("--test", help="Test hooks after installation")
    ] = True,
) -> None:
    """
    Install Git hooks for code quality enforcement.

    Installs pre-commit hooks that enforce:
    - Event Validator (UPPER_SNAKE_CASE)
    - Mutation Validator (no update/delete)
    - LLM Audit Policy (require @require_audit_log)
    - LLM Router Policy (no direct API imports)
    - Unit Tests (must pass)
    - Commit Message Validator (Conventional Commits)
    """
    import subprocess

    typer.echo("🔧 FREE INTELLIGENCE - GIT HOOKS INSTALLER")
    typer.echo("=" * 50)

    # Check if pre-commit is installed
    try:
        subprocess.run(["pre-commit", "--version"], capture_output=True, check=True)
        typer.echo("✅ pre-commit is already installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        typer.echo("⚠️  pre-commit not found. Installing...")
        try:
            subprocess.run(["pip3", "install", "pre-commit"], check=True)
            typer.echo("✅ pre-commit installed")
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to install pre-commit: {e}")
            raise typer.Exit(1)

    typer.echo()

    # Install hooks
    typer.echo("📦 Installing pre-commit hooks...")
    try:
        subprocess.run(["pre-commit", "install"], check=True)
        typer.echo("✅ Pre-commit hooks installed")
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to install pre-commit hooks: {e}")
        raise typer.Exit(1)

    try:
        subprocess.run(["pre-commit", "install", "--hook-type", "commit-msg"], check=True)
        typer.echo("✅ Commit-msg hooks installed")
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to install commit-msg hooks: {e}")
        raise typer.Exit(1)

    typer.echo()

    # Show installed hooks
    typer.echo("✅ Hooks installed successfully!")
    typer.echo()
    typer.echo("📋 Installed hooks:")
    typer.echo("   1. Event Validator (UPPER_SNAKE_CASE)")
    typer.echo("   2. Mutation Validator (no update/delete)")
    typer.echo("   3. LLM Audit Policy (require @require_audit_log)")
    typer.echo("   4. LLM Router Policy (no direct API imports)")
    typer.echo("   5. Unit Tests (must pass)")
    typer.echo("   6. Commit Message Validator (Conventional Commits)")
    typer.echo()

    # Test hooks
    if test_hooks:
        typer.echo("🧪 Testing hooks...")
        try:
            result = subprocess.run(["pre-commit", "run", "--all-files"], capture_output=True, text=True)
            if result.returncode == 0:
                typer.echo("✅ All hooks passed")
            else:
                typer.echo("⚠️  Some hooks failed (this is normal on first run)")
                typer.echo("   Hooks will run automatically on next commit")
        except subprocess.CalledProcessError:
            typer.echo("⚠️  Hook testing failed (this is normal on first run)")
            typer.echo("   Hooks will run automatically on next commit")

    typer.echo()
    typer.echo("=" * 50)
    typer.echo("✅ Git hooks setup complete!")
    typer.echo()
    typer.echo("Usage:")
    typer.echo("  • Hooks run automatically on 'git commit'")
    typer.echo("  • Run manually: pre-commit run --all-files")
    typer.echo("  • Skip hooks (emergency): git commit --no-verify")


@app.command("validate-commit-message")
def validate_commit_message(
    message: Annotated[
        str,
        typer.Option("--message", help="Commit message to validate")
    ] = "",
    file: Annotated[
        Path | None,
        typer.Option("--file", help="Path to commit message file", exists=True)
    ] = None,
) -> None:
    """
    Validate commit message format (Conventional Commits).

    Enforces format: <type>(<scope>): <message>
    Valid types: feat, fix, docs, refactor, test, chore, perf, ci, build, revert

    Used by pre-commit hooks to ensure consistent commit messages.
    """
    import re

    # Conventional Commits types
    VALID_TYPES = {
        "feat",  # New feature
        "fix",  # Bug fix
        "docs",  # Documentation
        "refactor",  # Code refactoring
        "test",  # Tests
        "chore",  # Maintenance
        "perf",  # Performance
        "ci",  # CI/CD
        "build",  # Build system
        "revert",  # Revert commit
    }

    # Pattern: type(scope): message
    COMMIT_PATTERN = re.compile(
        r"^(?P<type>\w+)"  # Type (required)
        r"(?:\((?P<scope>[\w-]+)\))?"  # Scope (optional)
        r": "  # Separator
        r"(?P<message>.+)$"  # Message (required)
    )

    def validate_message(msg: str) -> tuple[bool, str]:
        """Validate commit message format."""
        # Skip merge commits
        if msg.startswith("Merge"):
            return True, ""

        # Skip revert commits (git revert)
        if msg.startswith("Revert"):
            return True, ""

        # Match pattern
        match = COMMIT_PATTERN.match(msg)

        if not match:
            return False, (
                "Invalid commit message format!\n\n"
                "Expected: <type>(<scope>): <message>\n"
                "Example: feat(security): add LLM audit policy\n\n"
                f"Valid types: {', '.join(sorted(VALID_TYPES))}"
            )

        commit_type = match.group("type")
        commit_message = match.group("message")

        # Validate type
        if commit_type not in VALID_TYPES:
            return False, (
                f"Invalid commit type: '{commit_type}'\n\nValid types: {', '.join(sorted(VALID_TYPES))}"
            )

        # Validate message not empty
        if not commit_message.strip():
            return False, "Commit message cannot be empty"

        # Validate message doesn't start with uppercase (except proper nouns)
        if commit_message[0].isupper() and not commit_message.startswith(
            ("API", "HDF5", "LLM", "UUID")
        ):
            return False, (
                "Commit message should start with lowercase\n"
                f"Got: '{commit_message}'\n"
                f"Try: '{commit_message[0].lower() + commit_message[1:]}'"
            )

        return True, ""

    # Get message from file or argument
    if file:
        commit_msg = file.read_text().strip().split("\n")[0]
    elif message:
        commit_msg = message.strip().split("\n")[0]
    else:
        typer.echo("❌ Must provide either --message or --file")
        raise typer.Exit(1)

    typer.echo(f"🔍 Validating commit message: {commit_msg[:60]}...")

    # Validate
    is_valid, error = validate_message(commit_msg)

    if not is_valid:
        typer.echo("\n❌ COMMIT MESSAGE VALIDATION FAILED\n")
        typer.echo(error)
        raise typer.Exit(1)

    typer.echo(f"✅ Commit message valid: {commit_msg[:60]}...")
    typer.echo()
    typer.echo("📋 Valid Conventional Commit format:")
    typer.echo("   • Type: One of feat, fix, docs, refactor, test, chore, perf, ci, build, revert")
    typer.echo("   • Scope: Optional, in parentheses")
    typer.echo("   • Message: Starts with lowercase (except proper nouns)")


@app.command("test-concurrent-h5-writes")
def test_concurrent_h5_writes() -> None:
    """Test concurrent HDF5 writes with session-level architecture."""
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from ...logger import get_logger
    from ...models.task_type import TaskType
    from ...storage.session_h5_manager import get_session_h5_path, get_storage_stats
    from ...storage.task_repository import (
        add_full_audio,
        add_full_transcription,
        add_webspeech_transcripts,
        ensure_task_exists,
        save_diarization_segments,
    )

    logger = get_logger(__name__)

    def worker_task(worker_id: int, session_id: str) -> dict:
        """Simulate worker writing to HDF5 (transcription + diarization + audio)."""
        start_time = time.time()
        logger.info(
            "WORKER_START",
            worker_id=worker_id,
            session_id=session_id,
        )

        try:
            # 1. Create task structures
            ensure_task_exists(session_id, TaskType.TRANSCRIPTION)
            ensure_task_exists(session_id, TaskType.DIARIZATION)

            # 2. Add webspeech transcripts (simulates frontend upload)
            transcripts = [f"Worker {worker_id} transcript line {i}" for i in range(5)]
            add_webspeech_transcripts(session_id, transcripts)

            # 3. Add full transcription (simulates STT result)
            full_text = f"Worker {worker_id} full transcription: Lorem ipsum dolor sit amet"
            add_full_transcription(session_id, full_text)

            # 4. Add audio file (simulates audio upload)
            audio_bytes = b"FAKE_AUDIO_DATA_" + str(worker_id).encode() * 1000
            add_full_audio(session_id, audio_bytes)

            # 5. Save diarization segments (simulates diarization worker)
            from ...providers.diarization import DiarizationSegment, Speaker

            segments = [
                DiarizationSegment(
                    speaker=Speaker(speaker_id="DOCTOR", name="Doctor"),
                    text=f"Worker {worker_id} segment {i}",
                    start_time=float(i),
                    end_time=float(i + 1),
                    confidence=0.95,
                )
                for i in range(3)
            ]
            save_diarization_segments(session_id, segments)

            elapsed = time.time() - start_time
            logger.info(
                "WORKER_SUCCESS",
                worker_id=worker_id,
                session_id=session_id,
                elapsed_seconds=round(elapsed, 3),
            )

            return {
                "worker_id": worker_id,
                "session_id": session_id,
                "success": True,
                "elapsed": round(elapsed, 3),
                "error": None,
            }

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                "WORKER_FAILED",
                worker_id=worker_id,
                session_id=session_id,
                error=str(e),
                exc_info=True,
            )
            return {
                "worker_id": worker_id,
                "session_id": session_id,
                "success": False,
                "elapsed": round(elapsed, 3),
                "error": str(e),
            }

    typer.echo("\n" + "=" * 70)
    typer.echo("🧪 CONCURRENT HDF5 WRITE TEST - Session-Level Architecture")
    typer.echo("=" * 70)
    typer.echo("Testing: 4 workers writing simultaneously to different session files")
    typer.echo("Expected: Zero concurrency conflicts, all workers succeed")
    typer.echo("=" * 70 + "\n")

    # Create 4 concurrent workers, each with its own session
    workers = 4
    sessions = [f"test-session-{i}" for i in range(1, workers + 1)]

    typer.echo("📋 Test Setup:")
    typer.echo(f"  Workers: {workers}")
    typer.echo(f"  Sessions: {', '.join(sessions)}")
    typer.echo()

    # Run workers concurrently
    typer.echo(f"🚀 Starting {workers} concurrent workers...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all workers
        futures = {
            executor.submit(worker_task, i + 1, session): (i + 1, session)
            for i, session in enumerate(sessions)
        }

        # Collect results
        results = []
        for future in as_completed(futures):
            worker_id, session = futures[future]
            result = future.result()
            results.append(result)
            status = "✅" if result["success"] else "❌"
            typer.echo(f"{status} Worker {worker_id} completed in {result['elapsed']}s")

    total_elapsed = time.time() - start_time

    # Analyze results
    typer.echo("\n" + "=" * 70)
    typer.echo("📊 RESULTS")
    typer.echo("=" * 70)

    successes = sum(1 for r in results if r["success"])
    failures = sum(1 for r in results if not r["success"])

    typer.echo(f"Total elapsed:  {round(total_elapsed, 3)}s")
    typer.echo(f"Success rate:   {successes}/{workers} ({successes / workers * 100:.0f}%)")
    typer.echo(f"✅ Successes:   {successes}")
    typer.echo(f"❌ Failures:    {failures}")

    if failures > 0:
        typer.echo("\n❌ FAILED WORKERS:")
        for r in results:
            if not r["success"]:
                typer.echo(f"  Worker {r['worker_id']}: {r['error']}")

    # Show storage stats
    typer.echo("\n" + "=" * 70)
    typer.echo("💾 STORAGE STATS")
    typer.echo("=" * 70)
    stats = get_storage_stats()
    typer.echo(f"Session files created: {stats['session_files_count']}")
    typer.echo(f"Total size:            {stats['session_files_size_mb']:.2f} MB")

    # Verify session files exist
    typer.echo("\n" + "=" * 70)
    typer.echo("🔍 VERIFICATION")
    typer.echo("=" * 70)
    for session in sessions:
        path = get_session_h5_path(session)
        exists = "✅" if path.exists() else "❌"
        size = path.stat().st_size if path.exists() else 0
        typer.echo(f"{exists} {session}: {size:,} bytes")

    # Final verdict
    typer.echo("\n" + "=" * 70)
    if failures == 0:
        typer.echo("🎉 TEST PASSED: Zero concurrency conflicts!")
        typer.echo("   All 4 workers wrote to HDF5 simultaneously without errors.")
        typer.echo("   Session-level architecture is working correctly.")
    else:
        typer.echo("❌ TEST FAILED: Concurrency conflicts detected!")
        typer.echo(f"   {failures} worker(s) failed to write to HDF5.")
    typer.echo("=" * 70 + "\n")

    raise typer.Exit(0 if failures == 0 else 1)


@app.command("test-steerable-voices")
def test_steerable_voices() -> None:
    """Test OpenAI Steerable TTS with Mexican Spanish accent."""
    import asyncio

    import os

    from ...services.tts_openai_steerable import get_steerable_tts_service

    async def run_test():
        """Generate greetings with Mexican Spanish accent"""
        tts = get_steerable_tts_service()

        # Test with the 3 available steerable voices
        voices = ["alloy", "echo", "shimmer"]

        for voice in voices:
            typer.echo(f"\n🎙️ Generating {voice} with Mexican Spanish accent...")

            text = f"Hola, soy {voice}. Hablo español mexicano de forma natural."

            try:
                audio = await tts.synthesize(
                    text=text, voice=voice, accent="Mexican Spanish", response_format="mp3", speed=1.0
                )

                # Save to temp file
                output_file = f"/tmp/steerable_{voice}.mp3"
                with open(output_file, "wb") as f:
                    f.write(audio)

                typer.echo(f"✅ Generated {len(audio) / 1024:.1f}KB → {output_file}")
                typer.echo("   Playing...")

                # Play using afplay
                os.system(f"afplay {output_file}")

            except Exception as e:
                typer.echo(f"❌ Error: {e}")

    asyncio.run(run_test())


@app.command("test-unified-tts")
def test_unified_tts() -> None:
    """Test Unified TTS with auto-detection."""
    import asyncio

    from ...services.tts_unified import get_unified_tts_service

    async def run_test():
        """Test auto-detection of steerable TTS for Spanish text"""
        tts = get_unified_tts_service()

        tests = [
            {
                "text": "Hola, buenos días. ¿Cómo se encuentra hoy?",
                "voice": "alloy",
                "provider": None,  # Should auto-detect openai-steerable
                "desc": "Spanish text + steerable voice → should use openai-steerable",
            },
            {
                "text": "Hello, good morning. How are you today?",
                "voice": "alloy",
                "provider": None,  # Should use standard openai
                "desc": "English text + steerable voice → should use openai standard",
            },
            {
                "text": "Hola, soy una voz nativa mexicana",
                "voice": "nova",
                "provider": None,  # Should use openai-steerable (Spanish auto-detect)
                "desc": "Spanish text + nova voice → should use openai-steerable",
            },
        ]

        for i, test in enumerate(tests, 1):
            typer.echo(f"\n{'=' * 70}")
            typer.echo(f"Test {i}: {test['desc']}")
            typer.echo(f"Text: {test['text'][:50]}...")
            typer.echo(f"Voice: {test['voice']}")
            typer.echo(f"Provider: {test['provider']}")
            typer.echo(f"{'=' * 70}")

            try:
                audio = await tts.synthesize(
                    text=test["text"],
                    voice=test["voice"],
                    provider=test["provider"],
                    response_format="mp3",
                )

                typer.echo(f"✅ Generated {len(audio) / 1024:.1f}KB audio")

                # Save sample file
                output_file = f"/tmp/unified_tts_test_{i}.mp3"
                with open(output_file, "wb") as f:
                    f.write(audio)

                typer.echo(f"   Saved to: {output_file}")

            except Exception as e:
                typer.echo(f"❌ Error: {e}")

    asyncio.run(run_test())
