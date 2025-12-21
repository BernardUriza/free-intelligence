"""Intelligent lint fixing tool using qwen-code for complex Ruff issues."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from ..execution.executor import execute_qwen_code
from ..observability.logger import get_logger

logger = get_logger(__name__)


def parse_ruff_output(ruff_output: str) -> list[dict[str, Any]]:
    """Parse Ruff check output into structured issues.

    Args:
        ruff_output: Raw output from `ruff check`

    Returns:
        List of issue dictionaries with file, line, code, message
    """
    issues = []
    lines = ruff_output.strip().split('\n')

    # Pattern for Ruff output: file.py:line:col: code message
    pattern = r'^([^:]+):(\d+):(\d+): ([A-Z]\d+) (.+)$'

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = re.match(pattern, line)
        if match:
            file_path, line_num, col_num, code, message = match.groups()
            issues.append({
                'file': file_path,
                'line': int(line_num),
                'column': int(col_num),
                'code': code,
                'message': message,
                'severity': _get_severity_from_code(code),
            })

    return issues


def _get_severity_from_code(code: str) -> str:
    """Determine severity from Ruff error code."""
    if code.startswith('F'):  # Pyflakes
        return 'error'
    elif code.startswith('E'):  # pycodestyle
        return 'error'
    elif code.startswith('W'):  # pycodestyle warnings
        return 'warning'
    elif code.startswith('I'):  # isort
        return 'info'
    elif code.startswith('N'):  # pep8-naming
        return 'warning'
    elif code.startswith('UP'):  # pyupgrade
        return 'info'
    elif code.startswith('B'):  # flake8-bugbear
        return 'warning'
    elif code.startswith('A'):  # flake8-builtins
        return 'warning'
    elif code.startswith('C4'):  # flake8-comprehensions
        return 'info'
    elif code.startswith('SIM'):  # flake8-simplify
        return 'info'
    else:
        return 'unknown'


def generate_fix_prompt(issues: list[dict[str, Any]], file_path: str | None = None) -> str:
    """Generate a qwen-code prompt for fixing linting issues.

    Args:
        issues: List of parsed Ruff issues
        file_path: Specific file to focus on (optional)

    Returns:
        Natural language prompt for qwen-code
    """
    if file_path:
        # Focus on specific file
        file_issues = [issue for issue in issues if issue['file'] == file_path]
        if not file_issues:
            return f"Fix any linting issues in {file_path}"

        prompt = f"Fix the following linting issues in {file_path}:\n\n"
        for issue in file_issues[:10]:  # Limit to first 10 issues
            prompt += f"- Line {issue['line']}: {issue['code']} {issue['message']}\n"

        prompt += "\nPlease fix these issues following Python best practices and the project's coding standards."
        return prompt

    else:
        # Process all issues, group by file
        files = {}
        for issue in issues:
            if issue['file'] not in files:
                files[issue['file']] = []
            files[issue['file']].append(issue)

        prompt = "Fix linting issues across multiple files:\n\n"

        for file_path, file_issues in list(files.items())[:5]:  # Limit to 5 files
            prompt += f"**{file_path}:**\n"
            for issue in file_issues[:5]:  # Limit to 5 issues per file
                prompt += f"- Line {issue['line']}: {issue['code']} {issue['message']}\n"
            prompt += "\n"

        prompt += "Please fix these issues following Python best practices and the project's coding standards. Focus on the most critical issues first."
        return prompt


def run_ruff_check(repo_path: str | Path = ".") -> str:
    """Run Ruff check and return output.

    Args:
        repo_path: Repository path to check

    Returns:
        Ruff check output as string
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "backend/", "tests/"],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        logger.warning("Ruff check timed out")
        return ""
    except Exception as e:
        logger.error(f"Error running Ruff check: {e}")
        return ""


def process_ruff_output(
    ruff_output: str = "",
    file_path: str = "",
    repo_path: str | Path = ".",
    timeout: int = 600,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Process Ruff output and apply intelligent fixes.

    Args:
        ruff_output: Raw Ruff check output
        file_path: Specific file to fix
        repo_path: Repository path
        timeout: Maximum execution time
        dry_run: If True, show fixes without applying

    Returns:
        Dictionary with results
    """
    if not ruff_output and file_path:
        # Run Ruff check on specific file
        try:
            result = subprocess.run(
                [sys.executable, "-m", "ruff", "check", file_path],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            ruff_output = result.stdout + result.stderr
        except Exception as e:
            return {"error": f"Failed to run Ruff on {file_path}: {e}"}

    if not ruff_output:
        return {"error": "No Ruff output provided"}

    # Parse issues
    issues = parse_ruff_output(ruff_output)
    if not issues:
        return {"summary": "No issues found in Ruff output"}

    # Filter for complex issues that need AI help
    complex_issues = [issue for issue in issues if _is_complex_issue(issue)]

    if not complex_issues:
        return {
            "summary": f"Found {len(issues)} issues, but none require AI assistance. Use 'ruff check --fix' for simple fixes.",
            "issues_count": len(issues),
        }

    # Generate fix prompt
    prompt = generate_fix_prompt(complex_issues, file_path)

    if dry_run:
        return {
            "proposed_fixes": prompt,
            "issues_count": len(complex_issues),
            "total_issues": len(issues),
        }

    # Execute fix with qwen-code
    logger.info(f"Applying intelligent fixes for {len(complex_issues)} complex issues")

    result = execute_qwen_code(
        prompt=prompt,
        args="--yolo" if len(complex_issues) > 5 else "",  # Use --yolo for complex fixes
        repo_path=repo_path,
        timeout=timeout,
    )

    warnings = []
    if result["stderr"]:
        warnings.append(result["stderr"])

    return {
        "summary": f"Processed {len(complex_issues)} complex issues out of {len(issues)} total",
        "success": result["success"],
        "exit_code": result["exit_code"],
        "warnings": warnings,
        "issues_count": len(complex_issues),
        "total_issues": len(issues),
    }


def _is_complex_issue(issue: dict[str, Any]) -> bool:
    """Determine if an issue requires AI assistance vs simple --fix.

    Args:
        issue: Parsed Ruff issue

    Returns:
        True if issue needs AI help
    """
    # Simple fixes that Ruff can handle automatically
    simple_codes = {
        'E501',  # Line too long (can be auto-fixed)
        'I001',  # Import block is un-sorted
        'W291', 'W292', 'W293',  # Whitespace issues
        'E203',  # Whitespace before ':'
        'E302', 'E303', 'E304', 'E305', 'E306',  # Blank line issues
    }

    # Complex issues that need understanding of code intent
    complex_codes = {
        'F401',  # Unused import (needs to understand if really unused)
        'F841',  # Unused variable (needs context)
        'B008',  # Do not perform function calls in argument defaults
        'C416',  # Unnecessary list comprehension
        'SIM',   # Simplify code (various complex simplifications)
        'UP',    # Pyupgrade (syntax changes that may affect behavior)
        'N',     # Naming conventions (subjective)
        'A',     # Built-in shadowing (needs understanding)
        'B',     # Bugbear (various complex issues)
    }

    code = issue['code']

    # If it's a simple code, don't use AI
    if code in simple_codes:
        return False

    # If it's a complex code, use AI
    if any(code.startswith(prefix) for prefix in ['F', 'B', 'C4', 'SIM', 'UP', 'N', 'A']):
        return True

    # Default to simple for unknown codes
    return False