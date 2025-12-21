"""Simplified qwen-code CLI wrapper."""
from __future__ import annotations

import sys
import typer

from ..execution.executor import execute_qwen_code

app = typer.Typer(help="FI Coder - qwen-code CLI wrapper")


@app.command()
def execute(
    prompt: str = typer.Argument(..., help="Natural language prompt for qwen-code"),
    args: str = typer.Option("", "--args", help="Additional CLI arguments"),
    repo_path: str = typer.Option(".", "--repo", help="Working directory"),
    timeout: int = typer.Option(300, "--timeout", help="Maximum execution time (seconds)"),
) -> None:
    """Execute qwen-code with the given prompt.

    Example:
        fi-coder execute "fix typo in README.md"
        fi-coder execute "refactor authentication" --args="--yolo"
    """
    result = execute_qwen_code(
        prompt=prompt,
        args=args,
        repo_path=repo_path,
        timeout=timeout,
    )

    # Print output
    if result["stdout"]:
        print(result["stdout"], end="")

    if result["stderr"]:
        print(result["stderr"], end="", file=sys.stderr)

    # Exit with qwen-code's exit code
    sys.exit(result["exit_code"])


@app.command()
def lint_fix(
    ruff_output: str = typer.Option("", "--ruff-output", help="Ruff check output to process"),
    file_path: str = typer.Option("", "--file", help="Specific file to fix"),
    repo_path: str = typer.Option(".", "--repo", help="Working directory"),
    timeout: int = typer.Option(600, "--timeout", help="Maximum execution time (seconds)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show fixes without applying them"),
) -> None:
    """Execute intelligent fixes based on Ruff linting issues.

    This command processes Ruff output and generates automated solutions for complex problems.

    Examples:
        # Fix issues from Ruff output
        ruff check backend/ | fi-coder lint-fix --ruff-output=-

        # Fix specific file
        fi-coder lint-fix --file=backend/src/fi_coder/cli/main.py

        # Dry run to see proposed fixes
        fi-coder lint-fix --file=backend/src/fi_coder/cli/main.py --dry-run
    """
    from ..tools.lint_fix import process_ruff_output

    if ruff_output == "-" and not sys.stdin.isatty():
        # Read from stdin
        ruff_output = sys.stdin.read()

    if not ruff_output and not file_path:
        typer.echo("Error: Either --ruff-output or --file must be provided", err=True)
        sys.exit(1)

    try:
        result = process_ruff_output(
            ruff_output=ruff_output,
            file_path=file_path,
            repo_path=repo_path,
            timeout=timeout,
            dry_run=dry_run,
        )

        if dry_run:
            typer.echo("🔍 Dry run - proposed fixes:")
            typer.echo(result.get("proposed_fixes", ""))
        else:
            typer.echo("✅ Intelligent fixes applied")
            if result.get("summary"):
                typer.echo(f"Summary: {result['summary']}")

        if result.get("warnings"):
            typer.echo("⚠️  Warnings:", err=True)
            for warning in result["warnings"]:
                typer.echo(f"  - {warning}", err=True)

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
