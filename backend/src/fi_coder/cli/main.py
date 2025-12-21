"""Simplified qwen-code CLI wrapper."""
from __future__ import annotations

import sys
from pathlib import Path

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


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
