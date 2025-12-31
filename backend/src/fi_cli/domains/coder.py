from __future__ import annotations

from typing import Annotated

import sys
import typer
from backend.src.fi_coder.observability.metrics import MetricsCollector
from pathlib import Path

from .._common import resolve_repo_root, run_cmd

app = typer.Typer(name="coder", help="AI-powered code assistance and fixes", no_args_is_help=True)


BasePathOpt = Annotated[
    Path | None,
    typer.Option(
        "--base-path",
        help="Absolute path to repo root.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
]


@app.command("lint-fix")
def lint_fix(
    base_path: BasePathOpt = None,
    auto_fix: bool = typer.Option(True, "--auto-fix/--no-auto-fix", help="Automatically attempt to fix linting errors using AI"),
    max_fixes: int = typer.Option(20, "--max-fixes", help="Maximum number of errors to attempt to fix (default: 20)"),
) -> None:
    """Run Ruff linter and optionally fix errors using qwen-code AI."""
    repo_root = resolve_repo_root(base_path)

    # Initialize metrics collector for monitoring
    metrics = MetricsCollector()
    metrics.record_metric("lint_fix_started", 1.0, tags={"repo": str(repo_root)})

    # Run Ruff check
    typer.echo("Running Ruff linter...")
    ruff_cmd = ["ruff", "check", "backend/"]
    ruff_proc = run_cmd(ruff_cmd, cwd=repo_root, capture_output=True, check=False)

    if ruff_proc.stdout:
        typer.echo(ruff_proc.stdout)
    if ruff_proc.stderr:
        typer.echo(ruff_proc.stderr, err=True)

    error_count = 0
    if "Found" in ruff_proc.stderr:
        # Extract error count from output like "Found 3181 errors."
        try:
            error_line = next(line for line in ruff_proc.stderr.split('\n') if "Found" in line and "errors" in line)
            error_count = int(error_line.split()[1])
        except:
            error_count = 0

    metrics.record_metric("lint_errors_found", float(error_count))

    if ruff_proc.returncode == 0:
        typer.echo("✅ No linting errors found!")
        metrics.record_metric("lint_fix_success", 1.0)
        return

    if not auto_fix:
        typer.echo("Linting errors found. Run with --auto-fix to attempt automatic fixes.")
        metrics.record_metric("lint_fix_skipped", 1.0)
        sys.exit(ruff_proc.returncode)

    # If there are errors and auto_fix is enabled, use fi_coder to fix
    typer.echo("Attempting to fix linting errors with AI...")

    # Import fi_coder execute function
    try:
        from backend.src.fi_coder.execution.executor import execute_qwen_code
    except ImportError:
        typer.echo("❌ fi_coder not available. Install or configure qwen-code.", err=True)
        metrics.record_metric("lint_fix_failed", 1.0, tags={"reason": "import_error"})
        sys.exit(1)

    # Create a prompt based on ruff output
    ruff_output = ruff_proc.stdout + ruff_proc.stderr
    # Limit to max_fixes errors
    error_lines = [line for line in ruff_output.strip().split('\n') if ':' in line and 'backend/' in line][:max_fixes]

    typer.echo(f"Sending {len(error_lines)} errors to AI for fixing...")
    metrics.record_metric("lint_fix_attempted", float(len(error_lines)))

    fixed_count = 0
    for error_line in error_lines:
        # Parse error line, e.g., "backend/src/file.py:123: error message"
        try:
            parts = error_line.split(':', 2)
            if len(parts) >= 3:
                file_path = parts[0].strip()
                line_num = parts[1].strip()
                error_desc = parts[2].strip()
                prompt = f"Fix this Ruff linting error in file {file_path} at line {line_num}: {error_desc}\n\nPlease edit the file to fix this specific error."

                typer.echo(f"Fixing error in {file_path}:{line_num}")
                result = execute_qwen_code(
                    prompt=prompt,
                    args="--yolo",  # Allow risky changes
                    repo_path=str(repo_root),
                    timeout=300,  # 5 minutes per error
                )

                if result["exit_code"] == 0:
                    fixed_count += 1
                    typer.echo(f"✅ Fixed error in {file_path}")
                else:
                    typer.echo(f"❌ Failed to fix error in {file_path}")
            else:
                typer.echo(f"Could not parse error line: {error_line}")
        except Exception as e:
            typer.echo(f"Error processing {error_line}: {e}")

    typer.echo(f"Fixed {fixed_count} out of {len(error_lines)} errors.")
    metrics.record_metric("lint_fix_success", float(fixed_count))

    # Log final metrics
    typer.echo("Metrics collected:")
    stats = metrics.get_metric_stats("lint_fix_started")
    typer.echo(f"Fix attempts: {stats}")


@app.command("format-fix")
def format_fix(
    base_path: BasePathOpt = None,
    auto_fix: bool = typer.Option(True, "--auto-fix/--no-auto-fix", help="Automatically attempt to fix formatting issues using AI"),
    max_files: int = typer.Option(20, "--max-files", help="Maximum number of files to attempt to fix (default: 20)"),
) -> None:
    """Run Ruff formatter and optionally fix formatting issues using qwen-code AI."""
    repo_root = resolve_repo_root(base_path)

    # Run Ruff format check
    typer.echo("Running Ruff formatter...")
    ruff_cmd = ["ruff", "format", "backend/", "--check"]
    ruff_proc = run_cmd(ruff_cmd, cwd=repo_root, capture_output=True, check=False)

    if ruff_proc.returncode == 0:
        typer.echo("✅ All files are properly formatted!")
        return

    if not auto_fix:
        typer.echo("Formatting issues found. Run with --auto-fix to attempt automatic fixes.")
        typer.echo(ruff_proc.stdout)
        sys.exit(ruff_proc.returncode)

    # Use fi_coder to fix formatting issues
    typer.echo("Attempting to fix formatting issues with AI...")

    try:
        from backend.src.fi_coder.execution.executor import execute_qwen_code
    except ImportError:
        typer.echo("❌ fi_coder not available. Install or configure qwen-code.", err=True)
        sys.exit(1)

    # Create a general prompt for formatting issues
    prompt = f"Fix all formatting issues in up to {max_files} files in the backend directory according to Python best practices and PEP 8 standards. Use tools like ruff or black to ensure proper formatting."

    result = execute_qwen_code(
        prompt=prompt,
        args="--yolo",
        repo_path=str(repo_root),
        timeout=600,  # 10 minutes for formatting
    )

    if result["exit_code"] == 0:
        typer.echo("✅ Formatting issues fixed with AI assistance")
    else:
        typer.echo("❌ Failed to fix formatting issues with AI")
        sys.exit(result["exit_code"])


@app.command("type-check-fix")
def type_check_fix(
    base_path: BasePathOpt = None,
    auto_fix: bool = typer.Option(True, "--auto-fix/--no-auto-fix", help="Automatically attempt to fix type checking errors using AI"),
    max_errors: int = typer.Option(20, "--max-errors", help="Maximum number of type errors to attempt to fix (default: 20)"),
) -> None:
    """Run Pyright type checker and optionally fix type errors using qwen-code AI."""
    repo_root = resolve_repo_root(base_path)

    # Run Pyright type check
    typer.echo("Running Pyright type checker...")
    try:
        # Try to run pyright via uvx first, then global install
        pyright_cmd = ["uvx", "pyright", "backend/"]
        pyright_proc = run_cmd(pyright_cmd, cwd=repo_root, capture_output=True, check=False)
    except:
        # Fallback to global pyright
        pyright_cmd = ["pyright", "backend/"]
        pyright_proc = run_cmd(pyright_cmd, cwd=repo_root, capture_output=True, check=False)

    if pyright_proc.stdout:
        typer.echo(pyright_proc.stdout)
    if pyright_proc.stderr:
        typer.echo(pyright_proc.stderr, err=True)

    if pyright_proc.returncode == 0:
        typer.echo("✅ No type checking errors found!")
        return

    if not auto_fix:
        typer.echo("Type checking errors found. Run with --auto-fix to attempt automatic fixes.")
        sys.exit(pyright_proc.returncode)

    # Use fi_coder to fix type checking issues
    typer.echo("Attempting to fix type checking errors with AI...")

    try:
        from backend.src.fi_coder.execution.executor import execute_qwen_code
    except ImportError:
        typer.echo("❌ fi_coder not available. Install or configure qwen-code.", err=True)
        sys.exit(1)

    # Create a prompt based on pyright output
    pyright_output = pyright_proc.stdout + pyright_proc.stderr
    prompt = f"Fix up to {max_errors} of the following Pyright type checking errors in the backend code:\n\n{pyright_output}\n\nUpdate type annotations and fix any type-related issues."

    result = execute_qwen_code(
        prompt=prompt,
        args="--yolo",
        repo_path=str(repo_root),
        timeout=600,  # 10 minutes for type issues
    )

    if result["exit_code"] == 0:
        typer.echo("✅ Type checking errors fixed with AI assistance")
    else:
        typer.echo("❌ Failed to fix type checking errors with AI")
        sys.exit(result["exit_code"])


@app.command("lint-fix-worker")
def lint_fix_worker_cmd(
    batch_size: int = typer.Option(5, "--batch-size", help="Number of errors to fix in this batch (default: 5)"),
) -> None:
    """Run a single batch of lint fixing using the worker."""
    try:
        from backend.src.fi_workers.tasks.lint_fix_worker import lint_fix_worker
    except ImportError as e:
        typer.echo(f"❌ Failed to import lint_fix_worker: {e}", err=True)
        sys.exit(1)

    result = lint_fix_worker(batch_size)
    data = result
    typer.echo(f"✅ Batch completed: Fixed {data['result']['fixed_count']} errors, {data['result']['remaining_errors']} remaining, took {data['duration_seconds']:.2f}s")


@app.command("lint-fix-aurity-worker")
def lint_fix_aurity_worker_cmd(
    batch_size: int = typer.Option(5, "--batch-size", help="Number of errors to fix in this batch (default: 5)"),
) -> None:
    """Run a single batch of ESLint fixing for AURITY using the worker."""
    try:
        from backend.src.fi_workers.tasks.lint_fix_worker import lint_fix_aurity_worker
    except ImportError as e:
        typer.echo(f"❌ Failed to import lint_fix_aurity_worker: {e}", err=True)
        sys.exit(1)

    result = lint_fix_aurity_worker(batch_size)
    data = result
    typer.echo(f"✅ AURITY batch completed: Fixed {data['result']['fixed_count']} errors, {data['result']['remaining_errors']} remaining, took {data['duration_seconds']:.2f}s")


@app.command("lint-fix-aurity-cron")
def lint_fix_aurity_cron_cmd(
    sleep_seconds: int = typer.Option(60, "--sleep-seconds", help="Seconds to wait between batches (default: 60)"),
) -> None:
    """Run continuous AURITY ESLint fixing in batches (cron-like behavior)."""
    try:
        from backend.scripts.lint_fix_aurity_cron import main as cron_main
    except ImportError as e:
        typer.echo(f"❌ Failed to import lint_fix_aurity_cron: {e}", err=True)
        sys.exit(1)

    # Override sleep_seconds if provided
    import backend.scripts.lint_fix_aurity_cron as cron_module
    cron_module.sleep_seconds = sleep_seconds

    typer.echo(f"Starting continuous AURITY lint fixing with {sleep_seconds}s intervals...")
    cron_main()
