#!/usr/bin/env python3
"""Type Error Detection CLI.

Detects, categorizes, and exports type errors from Pylance/Pyright.

Usage:
    fi analysis detect-type-errors backend/
    fi analysis detect-type-errors backend/ --all
    fi analysis detect-type-errors backend/ --export
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class TypeCheckError:
    """Single type checking error."""

    file: str
    line: int
    column: int
    severity: str  # error, warning
    message: str
    rule: str  # e.g., reportArgumentType
    tool: str  # pyright, mypy, ruff


@dataclass
class TypeCheckResults:
    """Aggregated type checking results."""

    tool: str
    timestamp: str
    total_errors: int
    total_warnings: int
    errors_by_file: dict[str, int]
    errors_by_rule: dict[str, int]
    errors_by_severity: dict[str, int]
    details: list[TypeCheckError]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool": self.tool,
            "timestamp": self.timestamp,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "errors_by_file": self.errors_by_file,
            "errors_by_rule": self.errors_by_rule,
            "errors_by_severity": self.errors_by_severity,
            "details": [asdict(e) for e in self.details],
        }


def run_pyright(path: str) -> dict[str, Any] | None:
    """Run pyright and return JSON output."""
    try:
        print("🔍 Running Pyright...", file=sys.stderr)
        result = subprocess.run(
            ["pyright", path, "--outputjson"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode in (0, 1):  # 0 = success, 1 = has errors (valid)
            return json.loads(result.stdout)
        else:
            print(f"❌ Pyright error: {result.stderr}", file=sys.stderr)
            return None

    except FileNotFoundError:
        print(
            "⚠️  Pyright not found. Install with: npm install -g pyright",
            file=sys.stderr,
        )
        return None
    except subprocess.TimeoutExpired:
        print("❌ Pyright timeout", file=sys.stderr)
        return None


def run_mypy(path: str) -> dict[str, Any] | None:
    """Run mypy and return JSON output."""
    try:
        print("🔍 Running Mypy...", file=sys.stderr)
        result = subprocess.run(
            [
                "mypy",
                path,
                "--ignore-missing-imports",
                "--json",
                "--show-error-codes",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode in (0, 1):
            # Mypy outputs one JSON object per line
            errors = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    try:
                        errors.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            return {"errors": errors}
        else:
            print(f"⚠️  Mypy warnings: {result.stderr}", file=sys.stderr)
            return None

    except FileNotFoundError:
        print(
            "⚠️  Mypy not found. Install with: pip install mypy",
            file=sys.stderr,
        )
        return None
    except subprocess.TimeoutExpired:
        print("❌ Mypy timeout", file=sys.stderr)
        return None


def run_ruff(path: str) -> dict[str, Any] | None:
    """Run ruff and return JSON output."""
    try:
        print("🔍 Running Ruff...", file=sys.stderr)
        result = subprocess.run(
            ["ruff", "check", path, "--output-format=json"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode in (0, 1):
            try:
                return json.loads(result.stdout) if result.stdout else {"results": []}
            except json.JSONDecodeError:
                return {"results": []}
        else:
            print(f"⚠️  Ruff warnings: {result.stderr}", file=sys.stderr)
            return None

    except FileNotFoundError:
        print("⚠️  Ruff not found. Install with: pip install ruff", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("❌ Ruff timeout", file=sys.stderr)
        return None


def parse_pyright_errors(data: dict[str, Any]) -> list[TypeCheckError]:
    """Parse pyright JSON output."""
    errors: list[TypeCheckError] = []
    if not data:
        return errors

    for diag in data.get("generalDiagnostics", []):
        error = TypeCheckError(
            file=diag.get("file", "unknown"),
            line=diag.get("range", {}).get("start", {}).get("line", 0) + 1,
            column=diag.get("range", {}).get("start", {}).get("character", 0) + 1,
            severity=diag.get("severity", "unknown"),
            message=diag.get("message", ""),
            rule=diag.get("rule", "unknown"),
            tool="pyright",
        )
        errors.append(error)

    return errors


def parse_mypy_errors(data: dict[str, Any]) -> list[TypeCheckError]:
    """Parse mypy JSON output."""
    errors: list[TypeCheckError] = []
    if not data:
        return errors

    for error_obj in data.get("errors", []):
        error = TypeCheckError(
            file=error_obj.get("filename", "unknown"),
            line=error_obj.get("line", 0),
            column=error_obj.get("column", 0),
            severity="error" if "error" in error_obj.get("severity", "").lower() else "warning",
            message=error_obj.get("message", ""),
            rule=error_obj.get("code", "unknown"),
            tool="mypy",
        )
        errors.append(error)

    return errors


def parse_ruff_errors(data: dict[str, Any] | list[Any]) -> list[TypeCheckError]:
    """Parse ruff JSON output."""
    errors: list[TypeCheckError] = []
    if not data:
        return errors

    # Handle both list format (newer ruff) and dict format
    items = data if isinstance(data, list) else data.get("results", [])

    for item in items:
        if isinstance(item, dict):
            error = TypeCheckError(
                file=item.get("filename", "unknown"),
                line=item.get("location", {}).get("row", 0),
                column=item.get("location", {}).get("column", 0),
                severity="warning",
                message=item.get("message", ""),
                rule=item.get("code", "unknown"),
                tool="ruff",
            )
            errors.append(error)

    return errors


def aggregate_errors(errors: list[TypeCheckError]) -> TypeCheckResults:
    """Aggregate errors into results."""
    errors_by_file: dict[str, int] = {}
    errors_by_rule: dict[str, int] = {}
    errors_by_severity: dict[str, int] = {}

    for error in errors:
        errors_by_file[error.file] = errors_by_file.get(error.file, 0) + 1
        errors_by_rule[error.rule] = errors_by_rule.get(error.rule, 0) + 1
        errors_by_severity[error.severity] = errors_by_severity.get(error.severity, 0) + 1

    total_errors = errors_by_severity.get("error", 0)
    total_warnings = errors_by_severity.get("warning", 0)

    return TypeCheckResults(
        tool="pyright",  # Primary tool
        timestamp=datetime.now(UTC).isoformat(),
        total_errors=total_errors,
        total_warnings=total_warnings,
        errors_by_file=errors_by_file,
        errors_by_rule=errors_by_rule,
        errors_by_severity=errors_by_severity,
        details=errors,
    )


def print_summary(results: TypeCheckResults) -> None:
    """Print human-readable summary."""
    print("\n" + "=" * 60, file=sys.stderr)
    print(f"📊 Type Check Results ({results.tool})", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Errors: {results.total_errors}", file=sys.stderr)
    print(f"Warnings: {results.total_warnings}", file=sys.stderr)
    print(f"Files with issues: {len(results.errors_by_file)}", file=sys.stderr)
    print("", file=sys.stderr)

    if results.errors_by_rule:
        print("Top Rules:", file=sys.stderr)
        for rule, count in sorted(results.errors_by_rule.items(), key=lambda x: -x[1])[:5]:
            print(f"  - {rule}: {count}", file=sys.stderr)
        print("", file=sys.stderr)

    if results.errors_by_file:
        print("Top Files:", file=sys.stderr)
        for file, count in sorted(results.errors_by_file.items(), key=lambda x: -x[1])[:5]:
            print(f"  - {Path(file).name}: {count}", file=sys.stderr)
        print("", file=sys.stderr)

    print("=" * 60, file=sys.stderr)


def run(args: Sequence[str] | None = None) -> None:
    """Detect type errors with Pyright/Pylance."""
    import argparse

    parser = argparse.ArgumentParser(description="Detect type errors with Pyright/Pylance")
    parser.add_argument(
        "path", nargs="?", default="backend/", help="Path to check (e.g., backend/)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all tools (Pyright, Mypy, Ruff)",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export results as JSON to ops/type_check_results.json",
    )
    parser.add_argument(
        "--critical-only",
        action="store_true",
        help="Only show critical errors",
    )

    parsed = parser.parse_args(list(args or []))

    # Run pyright (always)
    pyright_data = run_pyright(parsed.path)
    pyright_errors = parse_pyright_errors(pyright_data) if pyright_data else []

    all_errors = pyright_errors

    # Run mypy if --all
    if parsed.all:
        mypy_data = run_mypy(parsed.path)
        mypy_errors = parse_mypy_errors(mypy_data) if mypy_data else []
        all_errors.extend(mypy_errors)

    # Run ruff if --all
    if parsed.all:
        ruff_data = run_ruff(parsed.path)
        ruff_errors = parse_ruff_errors(ruff_data) if ruff_data else []
        all_errors.extend(ruff_errors)

    # Filter if critical only
    if parsed.critical_only:
        all_errors = [e for e in all_errors if e.severity == "error"]

    # Aggregate
    results = aggregate_errors(all_errors)
    print_summary(results)

    # Export if requested
    if parsed.export:
        ops_dir = Path("ops/type_check_results")
        ops_dir.mkdir(parents=True, exist_ok=True)

        output_file = ops_dir / "results.json"
        with open(output_file, "w") as f:
            json.dump(results.to_dict(), f, indent=2)

        print(f"✅ Exported to {output_file}", file=sys.stderr)

    # Output JSON to stdout
    print(json.dumps(results.to_dict(), indent=2))


if __name__ == "__main__":
    run()
