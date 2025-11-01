#!/usr/bin/env python3
"""
Type Check Result Parsers

Unified parsers for pyright, mypy, and ruff JSON output.
Provides a common TypeCheckResult format for all tools.

Usage:
    from type_check_parsers import parse_pyright_output, parse_mypy_output, parse_ruff_output

Created: 2025-10-31
Project: Free Intelligence
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict

# ============================================================================
# Type Definitions
# ============================================================================


class Position(TypedDict):
    """Line/column position in a file (0-based)."""

    line: int  # 0-based
    character: int  # 0-based


class Range(TypedDict):
    """Range in a file."""

    start: Position
    end: Position


class PyrightDiagnostic(TypedDict):
    """Pyright diagnostic structure."""

    file: str
    severity: Literal["error", "warning", "information"]
    message: str
    range: Range
    rule: str  # May be missing


class RuffLocation(TypedDict):
    """Ruff location structure."""

    row: int
    column: int


class RuffDiagnostic(TypedDict):
    """Ruff diagnostic structure."""

    code: str
    message: str
    location: RuffLocation
    end_location: RuffLocation
    filename: str
    fix: dict[str, Any] | None  # Optional fix suggestion


# ============================================================================
# Common Result Format
# ============================================================================


@dataclass
class TypeCheckResult:
    """Unified type check result format."""

    file: str
    line: int  # 1-based for display
    column: int
    severity: str
    message: str
    rule: str

    @classmethod
    def from_pyright_diagnostic(cls, diag: PyrightDiagnostic) -> TypeCheckResult:
        """Convert pyright diagnostic to common format."""
        return cls(
            file=diag["file"],
            line=diag["range"]["start"]["line"] + 1,  # Convert to 1-based
            column=diag["range"]["start"]["character"],
            severity=diag["severity"],
            message=diag["message"],
            rule=diag.get("rule", "unknown"),
        )

    @classmethod
    def from_mypy_json(cls, data: dict[str, Any]) -> TypeCheckResult:
        """Convert mypy JSON output to common format."""
        return cls(
            file=data["file"],
            line=data["line"],
            column=data["column"],
            severity=data["severity"],
            message=data["message"],
            rule=data.get("code", "unknown"),
        )

    @classmethod
    def from_ruff_diagnostic(cls, diag: RuffDiagnostic) -> TypeCheckResult:
        """Convert ruff diagnostic to common format."""
        return cls(
            file=diag["filename"],
            line=diag["location"]["row"],
            column=diag["location"]["column"],
            severity="error",  # Ruff doesn't distinguish severity levels
            message=diag["message"],
            rule=diag["code"],
        )

    def __str__(self) -> str:
        """Human-readable format."""
        return (
            f"{self.file}:{self.line}:{self.column} [{self.severity}] {self.message} ({self.rule})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file": self.file,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "message": self.message,
            "rule": self.rule,
        }


# ============================================================================
# Parsers
# ============================================================================


def parse_pyright_output(json_file: str | Path) -> list[TypeCheckResult]:
    """
    Parse pyright JSON output into structured results.

    Args:
        json_file: Path to pyright --outputjson file

    Returns:
        List of TypeCheckResult objects

    Example:
        results = parse_pyright_output("pyright_results.json")
        for r in results:
            print(f"{r.file}:{r.line} - {r.message}")
    """
    with open(json_file) as f:
        data = json.load(f)

    results = []
    for diag in data.get("generalDiagnostics", []):
        results.append(TypeCheckResult.from_pyright_diagnostic(diag))

    return results


def parse_mypy_output(json_file: str | Path) -> list[TypeCheckResult]:
    """
    Parse mypy JSON output into structured results.

    Args:
        json_file: Path to mypy --output=json file

    Returns:
        List of TypeCheckResult objects

    Example:
        results = parse_mypy_output("mypy_results.json")
        errors = [r for r in results if r.severity == "error"]
    """
    results = []

    with open(json_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                results.append(TypeCheckResult.from_mypy_json(data))
            except json.JSONDecodeError:
                # Skip invalid lines
                continue

    return results


def parse_ruff_output(json_file: str | Path) -> list[TypeCheckResult]:
    """
    Parse ruff JSON output into structured results.

    Args:
        json_file: Path to ruff --output-format=json file

    Returns:
        List of TypeCheckResult objects

    Example:
        results = parse_ruff_output("ruff_results.json")
        unused_imports = [r for r in results if r.rule == "F401"]
    """
    with open(json_file) as f:
        data = json.load(f)

    results = []
    for item in data:
        results.append(TypeCheckResult.from_ruff_diagnostic(item))

    return results


# ============================================================================
# SARIF Export
# ============================================================================


def convert_to_sarif(results: list[TypeCheckResult], tool: str) -> dict[str, Any]:
    """
    Convert results to SARIF 2.1.0 format for GitHub Code Scanning.

    Args:
        results: List of type check results
        tool: Tool name (pyright, mypy, ruff)

    Returns:
        SARIF 2.1.0 compatible dictionary

    Example:
        sarif = convert_to_sarif(results, "pyright")
        with open("results.sarif", "w") as f:
            json.dump(sarif, f, indent=2)
    """
    return {
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": tool,
                        "version": "1.0.0",
                        "informationUri": f"https://github.com/{tool}",
                    }
                },
                "results": [
                    {
                        "ruleId": r.rule,
                        "level": "error" if r.severity == "error" else "warning",
                        "message": {"text": r.message},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": r.file},
                                    "region": {"startLine": r.line, "startColumn": r.column},
                                }
                            }
                        ],
                    }
                    for r in results
                ],
            }
        ],
    }


# ============================================================================
# Utilities
# ============================================================================


def filter_by_severity(results: list[TypeCheckResult], severity: str) -> list[TypeCheckResult]:
    """Filter results by severity level."""
    return [r for r in results if r.severity == severity]


def filter_by_rule(results: list[TypeCheckResult], rule: str) -> list[TypeCheckResult]:
    """Filter results by rule code."""
    return [r for r in results if r.rule == rule]


def filter_by_file(results: list[TypeCheckResult], file_pattern: str) -> list[TypeCheckResult]:
    """Filter results by file path pattern."""
    return [r for r in results if file_pattern in r.file]


def group_by_file(results: list[TypeCheckResult]) -> dict[str, list[TypeCheckResult]]:
    """Group results by file."""
    grouped: dict[str, list[TypeCheckResult]] = {}
    for result in results:
        if result.file not in grouped:
            grouped[result.file] = []
        grouped[result.file].append(result)
    return grouped


def group_by_rule(results: list[TypeCheckResult]) -> dict[str, list[TypeCheckResult]]:
    """Group results by rule."""
    grouped: dict[str, list[TypeCheckResult]] = {}
    for result in results:
        if result.rule not in grouped:
            grouped[result.rule] = []
        grouped[result.rule].append(result)
    return grouped


# ============================================================================
# Main (for testing)
# ============================================================================


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python type_check_parsers.py <tool> <json_file>")
        print("Tools: pyright, mypy, ruff")
        sys.exit(1)

    tool = sys.argv[1]
    json_file = sys.argv[2]

    if tool == "pyright":
        results = parse_pyright_output(json_file)
    elif tool == "mypy":
        results = parse_mypy_output(json_file)
    elif tool == "ruff":
        results = parse_ruff_output(json_file)
    else:
        print(f"Unknown tool: {tool}")
        sys.exit(1)

    print(f"Parsed {len(results)} results from {tool}")
    print()

    # Display summary
    errors = filter_by_severity(results, "error")
    warnings = filter_by_severity(results, "warning")

    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print()

    # Display first 10
    print("First 10 results:")
    for r in results[:10]:
        print(f"  {r}")
