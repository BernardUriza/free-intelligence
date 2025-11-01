# Python Type Checking Automation Guide
## Professional CI/CD Integration for Type Safety

**Project**: Free Intelligence
**Version**: 0.3.0
**Last Updated**: 2025-10-31
**Purpose**: Comprehensive guide for automated type checking with Pylance/Pyright, Mypy, and Ruff

---

## Table of Contents

1. [Overview](#overview)
2. [Type Checker Comparison](#type-checker-comparison)
3. [Current Project Setup](#current-project-setup)
4. [CLI Tools & Commands](#cli-tools--commands)
5. [Pre-commit Hooks](#pre-commit-hooks)
6. [CI/CD Integration](#cicd-integration)
7. [Output Formats & Parsing](#output-formats--parsing)
8. [Automation Workflows](#automation-workflows)
9. [Claude Code Integration](#claude-code-integration)
10. [Best Practices](#best-practices)

---

## Overview

Type checking in Python projects ensures code reliability and catches errors before runtime. This guide covers professional-grade automation for the Free Intelligence project, which uses:

- **68 Python modules** in `/backend` (all using `from typing import`)
- **FastAPI** for API endpoints
- **Healthcare-grade** reliability requirements
- **Mixed Python versions**: 3.9-3.12 support

### Goals

1. Automated type checking in development (pre-commit)
2. CI/CD enforcement (GitHub Actions)
3. Batch error detection and categorization
4. Integration with Claude Code for automated fixes

---

## Type Checker Comparison

### Pyright (Powers Pylance in VS Code)

**Strengths**:
- Fastest performance (written in TypeScript, runs on Node.js)
- Powers VS Code's Pylance extension
- Best IDE integration
- Implements new typing features quickly
- Rich JSON output format

**Installation**:
```bash
# Via npm (recommended for CI/CD)
npm install -g pyright

# Via pip (Python wrapper)
pip install pyright
```

**Use Cases**:
- VS Code users (already have it via Pylance)
- Fast CI/CD checks
- Projects prioritizing IDE experience

### Mypy

**Strengths**:
- Original and most widely adopted
- Comprehensive type checking
- Mature ecosystem
- Better community support
- Plugin system

**Installation**:
```bash
pip install mypy
```

**Use Cases**:
- Projects with complex type requirements
- Teams familiar with Python tooling
- Need for custom plugins

### Ruff

**Strengths**:
- Extremely fast linting (written in Rust)
- Replaces multiple tools (flake8, isort, etc.)
- Growing feature set
- **Note**: Not a type checker (yet)

**Type Checking**:
- Ruff is developing "Red Knot" type checker
- Currently use Ruff + Mypy/Pyright together
- Ruff for linting, type checker for types

**Installation**:
```bash
pip install ruff
```

---

## Current Project Setup

### Configuration Files

#### 1. `/pyrightconfig.json`
```json
{
  "include": ["backend", "tests"],
  "exclude": ["**/__pycache__", "**/.pytest_cache", "**/node_modules", "**/.venv", "**/venv"],
  "pythonVersion": "3.9",
  "typeCheckingMode": "standard",
  "reportAttributeAccessIssue": "error",
  "reportArgumentType": "error",
  "reportAssignmentType": "error",
  "reportOptionalMemberAccess": "error",
  "reportGeneralTypeIssues": "error",
  "reportUnusedImport": "error"
}
```

#### 2. `/pyproject.toml`
```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true

[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "SIM"]
ignore = ["E501"]
```

#### 3. `/.pre-commit-config.yaml`
Currently configured with:
- Ruff (linting + formatting)
- MyPy (strict mode)
- Bandit (security)
- Standard pre-commit hooks

---

## CLI Tools & Commands

### Pyright CLI

#### Basic Usage
```bash
# Check entire codebase
pyright backend/

# Check specific files
pyright backend/llm_router.py backend/corpus_ops.py

# Watch mode (re-run on changes)
pyright --watch backend/

# Generate JSON output (for automation)
pyright backend/ --outputjson > type_errors.json

# Specify Python version
pyright --pythonversion 3.11 backend/

# Use specific config file
pyright --project pyrightconfig.json
```

#### JSON Output Structure
```json
{
  "version": "1.1.xxx",
  "time": "2025-10-31T12:00:00.000Z",
  "generalDiagnostics": [
    {
      "file": "/path/to/file.py",
      "severity": "error",
      "message": "Argument of type 'str' cannot be assigned to parameter of type 'int'",
      "range": {
        "start": {"line": 42, "character": 10},
        "end": {"line": 42, "character": 15}
      },
      "rule": "reportArgumentType"
    }
  ],
  "summary": {
    "filesAnalyzed": 68,
    "errorCount": 12,
    "warningCount": 5,
    "informationCount": 0,
    "timeInSec": 1.234
  }
}
```

### Mypy CLI

#### Basic Usage
```bash
# Check entire codebase
mypy backend/

# Check with coverage report
mypy backend/ --html-report mypy_report/

# Generate JSON output
mypy backend/ --output json > mypy_errors.json

# Strict mode
mypy backend/ --strict

# Ignore missing imports
mypy backend/ --ignore-missing-imports

# Check specific Python version
mypy backend/ --python-version 3.11

# Show error codes
mypy backend/ --show-error-codes

# Generate JUnit XML for CI
mypy backend/ --junit-xml mypy_results.xml
```

#### JSON Output Format
```bash
# Using --output=json flag (requires mypy >= 1.0)
mypy backend/ --output=json

# Output structure:
{
  "file": "backend/llm_router.py",
  "line": 42,
  "column": 10,
  "severity": "error",
  "message": "Incompatible types in assignment",
  "code": "assignment",
  "errorCode": "assignment"
}
```

#### Third-Party JSON Tools
```bash
# Install mypy-json-report
pip install mypy-json-report

# Generate enhanced JSON report
mypy backend/ | mypy-json-report > mypy_detailed.json
```

### Ruff CLI

#### Linting
```bash
# Check code
ruff check backend/ tests/

# Auto-fix issues
ruff check backend/ tests/ --fix

# Show statistics
ruff check backend/ tests/ --statistics

# Output JSON
ruff check backend/ tests/ --output-format=json > ruff_errors.json

# Exit with code 0 (don't fail CI)
ruff check backend/ tests/ --exit-zero
```

#### Formatting
```bash
# Check formatting
ruff format backend/ tests/ --check

# Apply formatting
ruff format backend/ tests/

# Preview changes without applying
ruff format backend/ tests/ --diff
```

---

## Pre-commit Hooks

### Enhanced Configuration

Create `.pre-commit-config.yaml`:

```yaml
# Pre-commit configuration for Free Intelligence
# Healthcare-grade code quality enforcement

repos:
  # Ruff - Fast linting and formatting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.4  # Latest as of 2025
    hooks:
      - id: ruff
        args: [--fix, --exit-zero]
        name: "ruff: Lint and fix"
        stages: [pre-commit]

      - id: ruff-format
        name: "ruff: Format code"
        stages: [pre-commit]

  # Pyright - Fast type checking
  - repo: https://github.com/RobertCraigie/pyright-python
    rev: v1.1.389  # Latest as of 2025
    hooks:
      - id: pyright
        name: "pyright: Type checking"
        stages: [pre-commit]
        # IMPORTANT: Tell pyright where to find dependencies
        additional_dependencies: []
        # Configure venv path in pyrightconfig.json instead
        pass_filenames: false
        args: [--project, pyrightconfig.json]

  # MyPy - Comprehensive type checking (alternative/additional to pyright)
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0  # Latest as of 2025
    hooks:
      - id: mypy
        additional_dependencies:
          - types-PyYAML
          - types-requests
          - types-python-dateutil
          - pydantic>=2.0.0
          - fastapi>=0.104.0
        args:
          - --strict
          - --ignore-missing-imports
          - --warn-redundant-casts
          - --warn-unused-ignores
          - --show-error-codes
        name: "mypy: Type checking (strict)"
        stages: [pre-commit]
        # Only run on staged files (faster)
        pass_filenames: true

  # Bandit - Security scanning
  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.0
    hooks:
      - id: bandit
        args: [-c, .bandit, -r]
        name: "bandit: Security audit"
        stages: [pre-commit]
        exclude: ^(tests/|scripts/)

  # Standard pre-commit hooks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-yaml
        args: [--unsafe]
      - id: check-json
      - id: check-added-large-files
        args: [--maxkb=1000]
      - id: check-merge-conflict
      - id: end-of-file-fixer
      - id: trailing-whitespace

  # Import sorting
  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort
        name: "isort: Sort imports"
        args: [--profile=black, --line-length=100]
        stages: [pre-commit]

default_stages: [pre-commit]
fail_fast: false  # Run all hooks even if one fails
```

### Installation & Usage

```bash
# Install pre-commit
pip install pre-commit

# Install hooks (run once per clone)
pre-commit install

# Run manually on all files
pre-commit run --all-files

# Run specific hook
pre-commit run pyright --all-files
pre-commit run mypy --all-files

# Update hooks to latest versions
pre-commit autoupdate

# Skip hooks (emergency only)
git commit --no-verify -m "message"
```

### Handling Pyright/Mypy Dependency Issues

#### Problem
Pre-commit runs tools in isolated virtualenvs, so type checkers can't see your project dependencies.

#### Solution 1: Configure venvPath (Pyright)
Update `pyrightconfig.json`:
```json
{
  "venvPath": ".",
  "venv": "venv",
  "executionEnvironments": [
    {
      "root": ".",
      "pythonVersion": "3.9",
      "extraPaths": [
        "${workspaceFolder}",
        "${workspaceFolder}/backend"
      ]
    }
  ]
}
```

#### Solution 2: Add dependencies to pre-commit hook
```yaml
- id: mypy
  additional_dependencies:
    - types-PyYAML
    - types-requests
    - pydantic>=2.0.0
    - fastapi>=0.104.0
    # Add all typed dependencies your project uses
```

#### Solution 3: Skip type checking in pre-commit, run in CI only
Remove pyright/mypy from pre-commit, rely on CI/CD enforcement.

---

## CI/CD Integration

### GitHub Actions Workflows

#### Complete Type Safety Workflow

Create `.github/workflows/type-safety.yml`:

```yaml
name: Type Safety & Quality Gate

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  pyright-check:
    name: Pyright Type Checking
    runs-on: ubuntu-latest
    timeout-minutes: 10

    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Set up Node.js (for pyright)
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install pyright
        run: npm install -g pyright

      - name: Run pyright with JSON output
        run: |
          pyright backend/ --outputjson > pyright_results.json || true

      - name: Parse and display results
        run: |
          python -c "
          import json
          with open('pyright_results.json') as f:
              results = json.load(f)

          summary = results.get('summary', {})
          print(f'Files analyzed: {summary.get(\"filesAnalyzed\", 0)}')
          print(f'Errors: {summary.get(\"errorCount\", 0)}')
          print(f'Warnings: {summary.get(\"warningCount\", 0)}')
          print(f'Time: {summary.get(\"timeInSec\", 0):.2f}s')

          if summary.get('errorCount', 0) > 0:
              print('\n=== ERRORS ===')
              for diag in results.get('generalDiagnostics', []):
                  if diag['severity'] == 'error':
                      print(f'{diag[\"file\"]}:{diag[\"range\"][\"start\"][\"line\"]+1}: {diag[\"message\"]}')
              exit(1)
          "

      - name: Upload pyright results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: pyright-results-${{ matrix.python-version }}
          path: pyright_results.json
          retention-days: 30

  mypy-check:
    name: MyPy Type Checking
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
          pip install types-PyYAML types-requests types-python-dateutil

      - name: Run mypy with JSON output
        run: |
          mypy backend/ --output=json > mypy_results.json || true

      - name: Run mypy with JUnit XML
        run: |
          mypy backend/ --junit-xml mypy_junit.xml --ignore-missing-imports

      - name: Display mypy summary
        if: always()
        run: |
          mypy backend/ --show-error-codes --ignore-missing-imports || true

      - name: Upload mypy results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: mypy-results
          path: |
            mypy_results.json
            mypy_junit.xml
          retention-days: 30

  ruff-check:
    name: Ruff Linting
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install ruff
        run: pip install ruff

      - name: Run ruff check with JSON output
        run: |
          ruff check backend/ tests/ --output-format=json > ruff_results.json || true

      - name: Display ruff summary
        run: |
          ruff check backend/ tests/ --statistics

      - name: Upload ruff results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: ruff-results
          path: ruff_results.json
          retention-days: 30

  pre-commit-check:
    name: Pre-commit Hooks
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Run pre-commit
        uses: pre-commit/action@v3.0.1

  quality-gate:
    name: Quality Gate Summary
    runs-on: ubuntu-latest
    needs: [pyright-check, mypy-check, ruff-check, pre-commit-check]
    if: always()

    steps:
      - name: Check Quality Gate Status
        run: |
          echo "=== Quality Gate Results ==="
          echo "Pyright: ${{ needs.pyright-check.result }}"
          echo "MyPy: ${{ needs.mypy-check.result }}"
          echo "Ruff: ${{ needs.ruff-check.result }}"
          echo "Pre-commit: ${{ needs.pre-commit-check.result }}"

          if [[ "${{ needs.pyright-check.result }}" == "failure" || \
                "${{ needs.mypy-check.result }}" == "failure" || \
                "${{ needs.ruff-check.result }}" == "failure" || \
                "${{ needs.pre-commit-check.result }}" == "failure" ]]; then
            echo "❌ Quality Gate FAILED"
            exit 1
          else
            echo "✅ Quality Gate PASSED"
            exit 0
          fi
```

#### Using GitHub Actions from Marketplace

##### Option 1: Pyright Action
```yaml
- name: Run Pyright
  uses: jakebailey/pyright-action@v2
  with:
    version: '1.1.389'
    annotate: true  # Add PR comments
    level: 'error'  # Only fail on errors
```

##### Option 2: Python Lint Code Scanning (SARIF)
```yaml
- name: Python Type Checking with SARIF
  uses: advanced-security/python-lint-code-scanning-action@v1
  with:
    linter: pyright,mypy
    sarif-file: type-check-results.sarif

- name: Upload SARIF to GitHub Security
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: type-check-results.sarif
```

---

## Output Formats & Parsing

### Pyright JSON Output

#### Structure
```json
{
  "version": "1.1.389",
  "time": "2025-10-31T12:00:00.000Z",
  "generalDiagnostics": [
    {
      "file": "/path/to/backend/llm_router.py",
      "severity": "error",
      "message": "Argument of type 'str | None' cannot be assigned to parameter of type 'str'",
      "range": {
        "start": {"line": 42, "character": 10},
        "end": {"line": 42, "character": 25}
      },
      "rule": "reportArgumentType"
    }
  ],
  "summary": {
    "filesAnalyzed": 68,
    "errorCount": 12,
    "warningCount": 5,
    "informationCount": 0,
    "timeInSec": 1.234
  }
}
```

#### Python Parser
```python
import json
from typing import TypedDict, Literal
from dataclasses import dataclass

class Position(TypedDict):
    line: int  # 0-based
    character: int  # 0-based

class Range(TypedDict):
    start: Position
    end: Position

class Diagnostic(TypedDict):
    file: str
    severity: Literal["error", "warning", "information"]
    message: str
    range: Range
    rule: str  # Optional

@dataclass
class TypeCheckResult:
    file: str
    line: int  # 1-based for display
    column: int
    severity: str
    message: str
    rule: str

    @classmethod
    def from_pyright_diagnostic(cls, diag: Diagnostic) -> "TypeCheckResult":
        return cls(
            file=diag["file"],
            line=diag["range"]["start"]["line"] + 1,  # Convert to 1-based
            column=diag["range"]["start"]["character"],
            severity=diag["severity"],
            message=diag["message"],
            rule=diag.get("rule", "unknown")
        )

def parse_pyright_output(json_file: str) -> list[TypeCheckResult]:
    """Parse pyright JSON output into structured results."""
    with open(json_file) as f:
        data = json.load(f)

    results = []
    for diag in data.get("generalDiagnostics", []):
        results.append(TypeCheckResult.from_pyright_diagnostic(diag))

    return results

# Usage
results = parse_pyright_output("pyright_results.json")
for r in results:
    print(f"{r.file}:{r.line}:{r.column} [{r.severity}] {r.message} ({r.rule})")
```

### Mypy JSON Output

#### Using --output=json
```bash
mypy backend/ --output=json > mypy_results.json
```

#### Parser
```python
import json

def parse_mypy_output(json_file: str) -> list[TypeCheckResult]:
    """Parse mypy JSON output."""
    results = []
    with open(json_file) as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            results.append(TypeCheckResult(
                file=data["file"],
                line=data["line"],
                column=data["column"],
                severity=data["severity"],
                message=data["message"],
                rule=data.get("code", "unknown")
            ))
    return results
```

### Ruff JSON Output

#### Structure
```json
[
  {
    "code": "F401",
    "message": "'os' imported but unused",
    "location": {
      "row": 5,
      "column": 8
    },
    "end_location": {
      "row": 5,
      "column": 10
    },
    "filename": "backend/llm_router.py",
    "fix": {
      "content": "",
      "location": {"row": 5, "column": 0},
      "end_location": {"row": 6, "column": 0}
    }
  }
]
```

#### Parser
```python
def parse_ruff_output(json_file: str) -> list[TypeCheckResult]:
    """Parse ruff JSON output."""
    with open(json_file) as f:
        data = json.load(f)

    results = []
    for item in data:
        results.append(TypeCheckResult(
            file=item["filename"],
            line=item["location"]["row"],
            column=item["location"]["column"],
            severity="error",  # Ruff doesn't distinguish severity
            message=item["message"],
            rule=item["code"]
        ))
    return results
```

### SARIF Format (GitHub Code Scanning)

#### Convert to SARIF
```python
def convert_to_sarif(results: list[TypeCheckResult], tool: str) -> dict:
    """Convert results to SARIF 2.1.0 format for GitHub Code Scanning."""
    return {
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "runs": [{
            "tool": {
                "driver": {
                    "name": tool,
                    "version": "1.0.0",
                    "informationUri": f"https://github.com/{tool}"
                }
            },
            "results": [
                {
                    "ruleId": r.rule,
                    "level": "error" if r.severity == "error" else "warning",
                    "message": {"text": r.message},
                    "locations": [{
                        "physicalLocation": {
                            "artifactLocation": {"uri": r.file},
                            "region": {
                                "startLine": r.line,
                                "startColumn": r.column
                            }
                        }
                    }]
                }
                for r in results
            ]
        }]
    }

# Usage
sarif = convert_to_sarif(results, "pyright")
with open("results.sarif", "w") as f:
    json.dump(sarif, f, indent=2)
```

---

## Automation Workflows

### 1. Batch Error Detection Script

Create `tools/type_check_batch.py`:

```python
#!/usr/bin/env python3
"""
Batch type checking with error categorization and reporting.

Usage:
    python tools/type_check_batch.py --tool pyright
    python tools/type_check_batch.py --tool mypy --strict
    python tools/type_check_batch.py --all --export-sarif
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Literal

# Import the parsers from above
from type_check_parsers import (
    TypeCheckResult,
    parse_pyright_output,
    parse_mypy_output,
    parse_ruff_output,
    convert_to_sarif
)

class TypeCheckRunner:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backend_path = project_root / "backend"
        self.tests_path = project_root / "tests"
        self.results_dir = project_root / "ops" / "type_checks"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run_pyright(self) -> list[TypeCheckResult]:
        """Run pyright and parse results."""
        output_file = self.results_dir / "pyright_results.json"

        cmd = [
            "pyright",
            str(self.backend_path),
            "--outputjson"
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Pyright writes to stdout
        with open(output_file, "w") as f:
            f.write(result.stdout)

        return parse_pyright_output(output_file)

    def run_mypy(self, strict: bool = False) -> list[TypeCheckResult]:
        """Run mypy and parse results."""
        output_file = self.results_dir / "mypy_results.json"

        cmd = [
            "mypy",
            str(self.backend_path),
            "--output=json",
            "--show-error-codes",
            "--ignore-missing-imports"
        ]

        if strict:
            cmd.append("--strict")

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        with open(output_file, "w") as f:
            f.write(result.stdout)

        return parse_mypy_output(output_file)

    def run_ruff(self) -> list[TypeCheckResult]:
        """Run ruff and parse results."""
        output_file = self.results_dir / "ruff_results.json"

        cmd = [
            "ruff",
            "check",
            str(self.backend_path),
            str(self.tests_path),
            "--output-format=json"
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        with open(output_file, "w") as f:
            f.write(result.stdout)

        return parse_ruff_output(output_file)

    def categorize_errors(self, results: list[TypeCheckResult]) -> dict:
        """Categorize errors by type and severity."""
        categories = {
            "by_severity": defaultdict(list),
            "by_rule": defaultdict(list),
            "by_file": defaultdict(list),
            "critical": [],  # Healthcare-critical issues
        }

        # Healthcare-critical type rules
        critical_rules = {
            "reportArgumentType",
            "reportAssignmentType",
            "reportOptionalMemberAccess",
            "reportGeneralTypeIssues",
            "arg-type",
            "assignment",
            "call-arg",
        }

        for result in results:
            categories["by_severity"][result.severity].append(result)
            categories["by_rule"][result.rule].append(result)
            categories["by_file"][result.file].append(result)

            if result.rule in critical_rules and result.severity == "error":
                categories["critical"].append(result)

        return categories

    def generate_report(self, results: list[TypeCheckResult], tool: str) -> str:
        """Generate markdown report."""
        categories = self.categorize_errors(results)

        report = f"# Type Check Report: {tool}\n\n"
        report += f"**Date**: {datetime.now().isoformat()}\n"
        report += f"**Total Issues**: {len(results)}\n\n"

        # Summary by severity
        report += "## Summary by Severity\n\n"
        for severity, items in categories["by_severity"].items():
            report += f"- **{severity.upper()}**: {len(items)}\n"
        report += "\n"

        # Critical issues (healthcare-grade)
        if categories["critical"]:
            report += "## ⚠️ Critical Issues (Healthcare-Grade)\n\n"
            report += f"**Count**: {len(categories['critical'])}\n\n"
            for item in categories["critical"][:10]:  # Show top 10
                report += f"- `{Path(item.file).name}:{item.line}` - {item.message} ({item.rule})\n"
            report += "\n"

        # Top error types
        report += "## Top Error Types\n\n"
        sorted_rules = sorted(
            categories["by_rule"].items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        for rule, items in sorted_rules[:10]:
            report += f"- **{rule}**: {len(items)} occurrences\n"
        report += "\n"

        # Files with most errors
        report += "## Files with Most Errors\n\n"
        sorted_files = sorted(
            categories["by_file"].items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        for file, items in sorted_files[:10]:
            report += f"- `{Path(file).name}`: {len(items)} issues\n"
        report += "\n"

        # Detailed errors
        report += "## Detailed Errors\n\n"
        for result in results[:50]:  # Show first 50
            report += f"### {Path(result.file).name}:{result.line}:{result.column}\n"
            report += f"**Severity**: {result.severity}  \n"
            report += f"**Rule**: `{result.rule}`  \n"
            report += f"**Message**: {result.message}\n\n"

        if len(results) > 50:
            report += f"\n*... and {len(results) - 50} more issues*\n"

        return report

def main():
    parser = argparse.ArgumentParser(description="Batch type checking")
    parser.add_argument("--tool", choices=["pyright", "mypy", "ruff", "all"], default="all")
    parser.add_argument("--strict", action="store_true", help="Use strict mode (mypy)")
    parser.add_argument("--export-sarif", action="store_true", help="Export SARIF format")
    parser.add_argument("--json", action="store_true", help="Export JSON summary")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    runner = TypeCheckRunner(project_root)

    all_results = {}

    if args.tool in ["pyright", "all"]:
        print("\n=== Running Pyright ===")
        all_results["pyright"] = runner.run_pyright()

    if args.tool in ["mypy", "all"]:
        print("\n=== Running MyPy ===")
        all_results["mypy"] = runner.run_mypy(strict=args.strict)

    if args.tool in ["ruff", "all"]:
        print("\n=== Running Ruff ===")
        all_results["ruff"] = runner.run_ruff()

    # Generate reports
    for tool, results in all_results.items():
        print(f"\n=== {tool.upper()} Results ===")
        print(f"Total issues: {len(results)}")

        # Save markdown report
        report = runner.generate_report(results, tool)
        report_file = runner.results_dir / f"{tool}_report.md"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"Report saved: {report_file}")

        # Export SARIF
        if args.export_sarif:
            sarif = convert_to_sarif(results, tool)
            sarif_file = runner.results_dir / f"{tool}_results.sarif"
            with open(sarif_file, "w") as f:
                json.dump(sarif, f, indent=2)
            print(f"SARIF saved: {sarif_file}")

        # Export JSON summary
        if args.json:
            categories = runner.categorize_errors(results)
            summary = {
                "tool": tool,
                "total_issues": len(results),
                "by_severity": {k: len(v) for k, v in categories["by_severity"].items()},
                "by_rule": {k: len(v) for k, v in categories["by_rule"].items()},
                "critical_count": len(categories["critical"]),
            }
            json_file = runner.results_dir / f"{tool}_summary.json"
            with open(json_file, "w") as f:
                json.dump(summary, f, indent=2)
            print(f"JSON summary saved: {json_file}")

if __name__ == "__main__":
    main()
```

Make executable:
```bash
chmod +x tools/type_check_batch.py
```

Usage:
```bash
# Run all tools
python tools/type_check_batch.py --all --export-sarif --json

# Run pyright only
python tools/type_check_batch.py --tool pyright

# Run mypy in strict mode
python tools/type_check_batch.py --tool mypy --strict
```

### 2. Makefile Integration

Add to `/Makefile`:

```makefile
# ============================================================================
# Type Checking & Quality (Enhanced)
# ============================================================================

.PHONY: type-check type-check-pyright type-check-mypy type-check-all type-check-batch type-fix

type-check-pyright: ## Run pyright type checker
	@echo "🔍 Type checking with Pyright..."
	pyright backend/

type-check-mypy: ## Run mypy type checker
	@echo "🔍 Type checking with MyPy..."
	mypy backend/ --ignore-missing-imports --show-error-codes

type-check-ruff: ## Run ruff linter
	@echo "🔍 Linting with Ruff..."
	ruff check backend/ tests/ --statistics

type-check: type-check-pyright ## Alias for pyright (default)

type-check-all: ## Run all type checkers
	@echo "🔍 Running all type checkers..."
	@$(MAKE) type-check-pyright
	@$(MAKE) type-check-mypy
	@$(MAKE) type-check-ruff

type-check-batch: ## Batch type checking with reports
	@echo "📊 Running batch type checking..."
	python3 tools/type_check_batch.py --all --export-sarif --json
	@echo ""
	@echo "Reports generated in ops/type_checks/"
	@ls -lh ops/type_checks/*.md ops/type_checks/*.json ops/type_checks/*.sarif

type-check-ci: ## CI-friendly type checking (JSON output)
	@echo "🔍 CI Type Checking..."
	@mkdir -p ops/ci_results
	pyright backend/ --outputjson > ops/ci_results/pyright.json || true
	mypy backend/ --output=json > ops/ci_results/mypy.json || true
	ruff check backend/ tests/ --output-format=json > ops/ci_results/ruff.json || true
	@echo "✅ CI results saved to ops/ci_results/"
```

---

## Claude Code Integration

### Automated Error Fixing Workflow

#### 1. Export Errors for Claude

Create `tools/export_for_claude.py`:

```python
#!/usr/bin/env python3
"""
Export type errors in Claude Code-friendly format.

Generates a structured JSON file that Claude Code can use to:
1. Understand all type errors in the codebase
2. Prioritize fixes by severity and file
3. Apply batch fixes systematically

Usage:
    python tools/export_for_claude.py --tool pyright
    python tools/export_for_claude.py --all --priority critical
"""

import argparse
import json
from pathlib import Path
from typing import Literal
from dataclasses import dataclass, asdict

from type_check_batch import TypeCheckRunner, TypeCheckResult

@dataclass
class ClaudeFixTask:
    """A type error fix task for Claude Code."""
    id: str
    file: str
    line: int
    column: int
    severity: str
    rule: str
    message: str
    context_lines: list[str]  # 5 lines before + error line + 5 lines after
    priority: Literal["critical", "high", "medium", "low"]
    estimated_complexity: Literal["simple", "moderate", "complex"]

    def to_dict(self) -> dict:
        return asdict(self)

class ClaudeExporter:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.runner = TypeCheckRunner(project_root)

    def get_context_lines(self, file: str, line: int, before: int = 5, after: int = 5) -> list[str]:
        """Get context lines around an error."""
        try:
            with open(file) as f:
                lines = f.readlines()

            start = max(0, line - before - 1)
            end = min(len(lines), line + after)

            return [
                {
                    "line_num": i + 1,
                    "content": lines[i].rstrip(),
                    "is_error": i + 1 == line
                }
                for i in range(start, end)
            ]
        except Exception as e:
            return [{"error": str(e)}]

    def assign_priority(self, result: TypeCheckResult) -> str:
        """Assign fix priority based on severity and rule."""
        critical_rules = {
            "reportArgumentType",
            "reportAssignmentType",
            "reportOptionalMemberAccess",
            "reportGeneralTypeIssues",
        }

        if result.severity == "error" and result.rule in critical_rules:
            return "critical"
        elif result.severity == "error":
            return "high"
        elif result.severity == "warning":
            return "medium"
        else:
            return "low"

    def estimate_complexity(self, result: TypeCheckResult) -> str:
        """Estimate fix complexity."""
        simple_rules = {
            "reportUnusedImport",
            "reportUnusedVariable",
            "reportDuplicateImport",
        }

        complex_rules = {
            "reportGeneralTypeIssues",
            "reportIncompatibleMethodOverride",
        }

        if result.rule in simple_rules:
            return "simple"
        elif result.rule in complex_rules:
            return "complex"
        else:
            return "moderate"

    def create_fix_tasks(self, results: list[TypeCheckResult], tool: str) -> list[ClaudeFixTask]:
        """Convert type check results to Claude fix tasks."""
        tasks = []

        for idx, result in enumerate(results):
            task = ClaudeFixTask(
                id=f"{tool}_{idx}_{result.rule}",
                file=result.file,
                line=result.line,
                column=result.column,
                severity=result.severity,
                rule=result.rule,
                message=result.message,
                context_lines=self.get_context_lines(result.file, result.line),
                priority=self.assign_priority(result),
                estimated_complexity=self.estimate_complexity(result)
            )
            tasks.append(task)

        return tasks

    def export_for_claude(
        self,
        tool: str,
        priority_filter: str | None = None,
        max_tasks: int | None = None
    ) -> dict:
        """Export errors in Claude-friendly format."""
        # Run type checker
        if tool == "pyright":
            results = self.runner.run_pyright()
        elif tool == "mypy":
            results = self.runner.run_mypy()
        elif tool == "ruff":
            results = self.runner.run_ruff()
        else:
            raise ValueError(f"Unknown tool: {tool}")

        # Convert to fix tasks
        tasks = self.create_fix_tasks(results, tool)

        # Filter by priority
        if priority_filter:
            tasks = [t for t in tasks if t.priority == priority_filter]

        # Limit tasks
        if max_tasks:
            tasks = tasks[:max_tasks]

        # Create export structure
        export = {
            "metadata": {
                "tool": tool,
                "total_errors": len(results),
                "total_tasks": len(tasks),
                "priority_filter": priority_filter,
                "project_root": str(self.project_root),
            },
            "tasks": [t.to_dict() for t in tasks],
            "stats": {
                "by_priority": self._count_by(tasks, "priority"),
                "by_complexity": self._count_by(tasks, "estimated_complexity"),
                "by_severity": self._count_by(tasks, "severity"),
                "by_file": self._count_by(tasks, "file"),
            },
            "claude_instructions": {
                "approach": "systematic_batch_fixing",
                "order": ["critical", "high", "medium", "low"],
                "batch_size": 10,
                "verification": "run type checker after each batch",
                "commit_strategy": "commit after each successful batch"
            }
        }

        return export

    @staticmethod
    def _count_by(tasks: list[ClaudeFixTask], attr: str) -> dict:
        """Count tasks by attribute."""
        counts = {}
        for task in tasks:
            value = getattr(task, attr)
            counts[value] = counts.get(value, 0) + 1
        return counts

def main():
    parser = argparse.ArgumentParser(description="Export type errors for Claude Code")
    parser.add_argument("--tool", choices=["pyright", "mypy", "ruff"], required=True)
    parser.add_argument("--priority", choices=["critical", "high", "medium", "low"])
    parser.add_argument("--max-tasks", type=int, help="Limit number of tasks")
    parser.add_argument("--output", help="Output file", default="ops/claude_fix_tasks.json")
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    exporter = ClaudeExporter(project_root)

    print(f"Exporting {args.tool} errors for Claude Code...")
    export = exporter.export_for_claude(
        tool=args.tool,
        priority_filter=args.priority,
        max_tasks=args.max_tasks
    )

    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(export, f, indent=2)

    print(f"\n✅ Exported {export['metadata']['total_tasks']} tasks to {output_file}")
    print(f"\nStats:")
    print(f"  By Priority: {export['stats']['by_priority']}")
    print(f"  By Complexity: {export['stats']['by_complexity']}")
    print(f"\nClaude Instructions:")
    print(f"  Approach: {export['claude_instructions']['approach']}")
    print(f"  Batch Size: {export['claude_instructions']['batch_size']}")
    print(f"\nNext steps:")
    print(f"  1. Review: cat {output_file} | jq '.stats'")
    print(f"  2. Fix with Claude Code: Load tasks and process in batches")
    print(f"  3. Verify: make type-check-{args.tool}")

if __name__ == "__main__":
    main()
```

#### 2. Claude Code Prompt Template

Create `.claude/commands/fix-types.md`:

```markdown
# Fix Type Errors (Batch Processing)

You are reviewing type checking errors from the Free Intelligence Python project.

## Context

This is a healthcare-grade application with strict type safety requirements:
- **68 Python modules** in `backend/`
- All files use `from typing import` annotations
- FastAPI endpoints with Pydantic models
- Type checking enforced in CI/CD (GitHub Actions)

## Your Task

Fix type errors systematically using this workflow:

### 1. Load Error Report
```bash
cat ops/claude_fix_tasks.json | jq '.metadata'
```

### 2. Review Stats
```bash
cat ops/claude_fix_tasks.json | jq '.stats'
```

### 3. Process in Batches

**Batch Size**: 10 errors at a time
**Order**: Critical → High → Medium → Low

For each batch:

1. **Read the error context**:
   ```bash
   cat ops/claude_fix_tasks.json | jq '.tasks[0:10]'
   ```

2. **Fix each error**:
   - Read the file
   - Understand the type error
   - Apply minimal fix (don't over-engineer)
   - Preserve existing code style
   - Add type hints where missing

3. **Verify fixes**:
   ```bash
   pyright backend/[fixed_file].py
   ```

4. **Commit batch**:
   ```bash
   git add backend/[files]
   git commit -m "fix(types): resolve [rule] errors in [files] (batch 1/N)"
   ```

5. **Run full type check**:
   ```bash
   make type-check-all
   ```

### 4. Repeat Until Complete

Continue with next batch until all errors are fixed.

## Common Fixes

### Missing Type Hints
```python
# Before
def process_data(data):
    return data.upper()

# After
def process_data(data: str) -> str:
    return data.upper()
```

### Optional Types
```python
# Before
def get_user(id: int) -> User:
    return db.get(id)  # May return None

# After
from typing import Optional

def get_user(id: int) -> Optional[User]:
    return db.get(id)
```

### Type Narrowing
```python
# Before
def process(value: str | None):
    return value.upper()  # Error: value might be None

# After
def process(value: str | None):
    if value is None:
        return None
    return value.upper()
```

### Union Types
```python
# Before
def handle(data: dict):
    if isinstance(data, list):  # Inconsistent
        return data[0]

# After
from typing import Union

def handle(data: Union[dict, list]) -> Any:
    if isinstance(data, list):
        return data[0] if data else None
    return data
```

## Guidelines

1. **Minimal Changes**: Only fix what's necessary
2. **Preserve Intent**: Don't change business logic
3. **Healthcare-Grade**: Be extra careful with medical data types
4. **Test**: Verify each fix doesn't break tests
5. **Document**: Add docstrings if type signature is complex

## Verification

After all fixes:
```bash
# Type checking
make type-check-all

# Tests
make test

# Pre-commit
pre-commit run --all-files

# CI simulation
python tools/type_check_batch.py --all --export-sarif
```

## Success Criteria

- ✅ All critical errors fixed
- ✅ All high-priority errors fixed
- ✅ Type checkers pass (pyright, mypy)
- ✅ Tests pass
- ✅ Pre-commit hooks pass
- ✅ CI/CD workflow passes

Report final stats:
```bash
python tools/type_check_batch.py --all --json
cat ops/type_checks/*_summary.json
```
```

#### 3. Usage with Claude Code

```bash
# 1. Export errors for Claude
python tools/export_for_claude.py --tool pyright --priority critical

# 2. Open in Claude Code
# Load the fix-types command
/fix-types

# 3. Claude will:
#    - Load ops/claude_fix_tasks.json
#    - Process 10 errors at a time
#    - Apply fixes
#    - Verify each batch
#    - Commit systematically

# 4. Monitor progress
git log --oneline | grep "fix(types)"

# 5. Final verification
make type-check-all
```

---

## Best Practices

### 1. Incremental Adoption

**Start Small**:
```bash
# Phase 1: Fix critical errors only
python tools/export_for_claude.py --tool pyright --priority critical --max-tasks 20

# Phase 2: Add type hints to new code
# Update pre-commit to enforce types on changed files only

# Phase 3: Fix remaining errors incrementally
# One module at a time, highest-value first
```

### 2. Type Checking Levels

**Strict Mode** (for new code):
```json
// pyrightconfig.json - per-file configuration
{
  "executionEnvironments": [
    {
      "root": "backend/api",
      "typeCheckingMode": "strict"  // New APIs
    },
    {
      "root": "backend",
      "typeCheckingMode": "standard"  // Legacy
    }
  ]
}
```

### 3. CI/CD Strategy

**Progressive Enforcement**:
```yaml
# .github/workflows/type-safety.yml

# Stage 1: Warning only (don't fail CI)
- name: Type check (warning)
  run: pyright backend/ || true

# Stage 2: Fail on critical errors only
- name: Critical type errors
  run: |
    pyright backend/ --outputjson > results.json
    python tools/check_critical_only.py results.json

# Stage 3: Full enforcement (after cleanup)
- name: Type check (strict)
  run: pyright backend/  # Fail on any error
```

### 4. Developer Workflow

**Local Development**:
```bash
# Before committing
make type-check-all  # Run all checkers

# Quick check (pyright is fastest)
make type-check

# Fix auto-fixable issues
ruff check backend/ tests/ --fix

# Run pre-commit
pre-commit run --all-files
```

### 5. Documentation

**Type Hint Style Guide**:
```python
from typing import Optional, Union, List, Dict, Any, TypedDict, Protocol

# ✅ Good: Explicit and clear
def process_user(
    user_id: int,
    name: str,
    email: Optional[str] = None
) -> Dict[str, Any]:
    """Process user data.

    Args:
        user_id: Unique user identifier
        name: User's full name
        email: Optional email address

    Returns:
        Dictionary with processing results
    """
    pass

# ❌ Bad: Missing types
def process_user(user_id, name, email=None):
    pass
```

### 6. Performance Optimization

**Caching**:
```bash
# Pyright uses file-based cache automatically
# Location: node_modules/.cache/pyright

# Mypy cache
mypy backend/ --cache-dir .mypy_cache

# CI caching (GitHub Actions)
- uses: actions/cache@v3
  with:
    path: |
      ~/.cache/pip
      node_modules/.cache/pyright
      .mypy_cache
    key: ${{ runner.os }}-type-check-${{ hashFiles('**/requirements.txt') }}
```

### 7. Error Suppression (Use Sparingly)

**Pyright**:
```python
# Suppress specific error
value = some_function()  # type: ignore[reportArgumentType]

# Suppress entire line
x = y  # pyright: ignore
```

**Mypy**:
```python
# Suppress specific error
value = some_function()  # type: ignore[arg-type]

# Suppress entire line
x = y  # type: ignore
```

**Better Alternative**: Fix the root cause!

---

## Recommended Setup for Free Intelligence

### Phase 1: Foundation (Week 1)

```bash
# 1. Install tools
pip install -e ".[dev]"  # Already includes mypy, ruff
npm install -g pyright

# 2. Update pre-commit (already configured)
pre-commit install

# 3. Run baseline check
python tools/type_check_batch.py --all --export-sarif --json

# 4. Review results
cat ops/type_checks/pyright_summary.json | jq
```

### Phase 2: Critical Fixes (Week 2)

```bash
# 1. Export critical errors for Claude
python tools/export_for_claude.py --tool pyright --priority critical

# 2. Fix with Claude Code
# Use /fix-types command

# 3. Verify
make type-check-all
make test
```

### Phase 3: CI/CD Integration (Week 3)

```bash
# 1. Already have quality-gate.yml workflow
# 2. Add type-safety.yml with SARIF upload (see above)
# 3. Enable branch protection requiring type checks

# GitHub Settings → Branches → main → Branch protection rules:
# ✅ Require status checks to pass before merging
# ✅ Type Safety & Quality Gate
```

### Phase 4: Continuous Improvement (Ongoing)

```bash
# Weekly type check report
python tools/type_check_batch.py --all --json
git add ops/type_checks/
git commit -m "chore: weekly type check report"

# New code: strict mode
# Update pyrightconfig.json to use "strict" for new modules

# Developer onboarding
# Include type checking in docs/CONTRIBUTING.md
```

---

## Tools Reference

### Installation

```bash
# Python tools (via pip)
pip install mypy ruff pre-commit pytest pytest-cov
pip install types-PyYAML types-requests types-python-dateutil

# Pyright (via npm)
npm install -g pyright

# Or via pip (Python wrapper)
pip install pyright
```

### Version Pinning

```toml
# pyproject.toml
[project.optional-dependencies]
dev = [
    "mypy==1.13.0",
    "pyright==1.1.389",
    "ruff==0.7.4",
    "pre-commit==4.0.0",
    "types-PyYAML==6.0.12",
    "types-requests==2.31.0",
    "types-python-dateutil==2.8.19",
]
```

### Command Aliases

Add to `~/.bashrc` or `~/.zshrc`:
```bash
alias tc='pyright backend/'
alias tcj='pyright backend/ --outputjson'
alias tcm='mypy backend/ --ignore-missing-imports'
alias tcr='ruff check backend/ tests/'
alias tca='make type-check-all'
```

---

## Troubleshooting

### Issue: Pyright can't find dependencies

**Solution**: Configure venvPath in `pyrightconfig.json`:
```json
{
  "venvPath": ".",
  "venv": "venv"
}
```

### Issue: Mypy too slow on large codebase

**Solutions**:
```bash
# 1. Use incremental mode (default)
mypy backend/ --cache-dir .mypy_cache

# 2. Use faster cache format (experimental)
mypy backend/ --fixed-format-cache

# 3. Run on changed files only
git diff --name-only | grep '\.py$' | xargs mypy
```

### Issue: Too many false positives

**Solutions**:
```bash
# 1. Adjust strictness
# pyrightconfig.json: "typeCheckingMode": "basic"

# 2. Ignore specific rules
# pyrightconfig.json: "reportUnusedVariable": "off"

# 3. Ignore specific imports
# pyproject.toml: [[tool.mypy.overrides]]
```

### Issue: Pre-commit hooks too slow

**Solutions**:
```bash
# 1. Run only on changed files (default)
pre-commit run  # Fast

# 2. Skip type checking in pre-commit, run in CI only
# Remove mypy/pyright from .pre-commit-config.yaml

# 3. Use pre-push instead of pre-commit
pre-commit install --hook-type pre-push
```

---

## Further Reading

- [Pyright Documentation](https://github.com/microsoft/pyright/blob/main/docs/README.md)
- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Python Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
- [FastAPI Type Hints Guide](https://fastapi.tiangolo.com/python-types/)
- [Pre-commit Documentation](https://pre-commit.com/)

---

## Appendix: Complete File Listing

### Created Files

1. `/docs/TYPE_CHECKING_AUTOMATION_GUIDE.md` (this file)
2. `/tools/type_check_batch.py` - Batch type checking runner
3. `/tools/type_check_parsers.py` - JSON parsers for all tools
4. `/tools/export_for_claude.py` - Claude Code integration
5. `/tools/check_critical_only.py` - CI critical-only checker
6. `/.claude/commands/fix-types.md` - Claude Code command
7. `/.github/workflows/type-safety.yml` - Enhanced CI workflow

### Modified Files

1. `/Makefile` - Added type-check-* targets
2. `/.pre-commit-config.yaml` - Enhanced with pyright
3. `/pyrightconfig.json` - Optimized configuration

---

**End of Guide**

For questions or issues, see:
- Project: `CLAUDE.md`
- Trello: Board ID `68fbfeeb7f8614df2eb61e42`
- GitHub: `.github/workflows/quality-gate.yml`
