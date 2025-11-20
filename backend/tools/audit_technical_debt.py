#!/usr/bin/env python3
"""
Technical Debt Audit & Validation Tool

Usage:
    python3 backend/tools/audit_technical_debt.py              # Full audit
    python3 backend/tools/audit_technical_debt.py --fix-quick  # Apply quick wins
    python3 backend/tools/audit_technical_debt.py --check      # Just show issues
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Issue:
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str
    file: str
    line: int | None
    message: str
    count: int = 1


class TechnicalDebtAuditor:
    def __init__(self, backend_dir: Path = Path("backend")):
        self.backend_dir = backend_dir
        self.issues: list[Issue] = []

    def audit_broad_exceptions(self) -> list[Issue]:
        """Find bare `except Exception` handlers."""
        issues = []
        pattern = r"^\s*except\s+Exception\s*:"

        for py_file in self.backend_dir.rglob("*.py"):
            with open(py_file) as f:
                for i, line in enumerate(f, 1):
                    if re.match(pattern, line):
                        # Check if there are specific exceptions above
                        with open(py_file) as f2:
                            lines = f2.readlines()
                            above = "".join(lines[max(0, i - 5) : i])
                            has_specific = len(re.findall(r"except\s+\w+", above)) > 1

                        if not has_specific:
                            issues.append(
                                Issue(
                                    severity="CRITICAL",
                                    category="broad_exception",
                                    file=str(py_file),
                                    line=i,
                                    message="Bare `except Exception` without specific types above",
                                )
                            )
        return issues

    def audit_type_ignore_comments(self) -> list[Issue]:
        """Count `# type: ignore` comments."""
        count = 0
        pattern = r"#\s*type:\s*ignore"

        for py_file in self.backend_dir.rglob("*.py"):
            with open(py_file) as f:
                for line in f:
                    if re.search(pattern, line):
                        count += 1

        if count > 50:
            return [
                Issue(
                    severity="CRITICAL",
                    category="type_ignore_count",
                    file="backend/**/*.py",
                    line=None,
                    message=f"{count} `# type: ignore` comments found",
                    count=count,
                )
            ]
        return []

    def audit_optional_usage(self) -> list[Issue]:
        """Find old-style `Optional[T]` (should be `Optional[T]`)."""
        issues = []
        pattern = r"Optional\["

        for py_file in self.backend_dir.rglob("*.py"):
            with open(py_file) as f:
                for i, line in enumerate(f, 1):
                    if "__future__" in line:  # Skip __future__ imports
                        continue
                    if re.search(pattern, line) and "typing" not in line:
                        issues.append(
                            Issue(
                                severity="MEDIUM",
                                category="optional_syntax",
                                file=str(py_file),
                                line=i,
                                message="Use `Optional[T]` instead of `Optional[T]` (PEP 604)",
                            )
                        )
        return issues

    def audit_large_functions(self, threshold: int = 100) -> list[Issue]:
        """Find functions with >100 lines."""
        issues = []

        for py_file in self.backend_dir.rglob("*.py"):
            with open(py_file) as f:
                lines = f.readlines()

            current_func = None
            func_start = 0

            for i, line in enumerate(lines):
                if re.match(r"^def\s+(\w+)", line):
                    # Check previous function
                    if current_func and i - func_start > threshold:
                        issues.append(
                            Issue(
                                severity="HIGH",
                                category="large_function",
                                file=str(py_file),
                                line=func_start + 1,
                                message=f"Function `{current_func}` is {i - func_start} lines",
                            )
                        )

                    match = re.match(r"^def\s+(\w+)", line)
                    current_func = match.group(1) if match else None  # type: ignore[union-attr]
                    func_start = i

            # Check last function
            if current_func and len(lines) - func_start > threshold:
                issues.append(
                    Issue(
                        severity="HIGH",
                        category="large_function",
                        file=str(py_file),
                        line=func_start + 1,
                        message=f"Function `{current_func}` is {len(lines) - func_start} lines",
                    )
                )

        return issues

    def audit_missing_error_handling(self) -> list[Issue]:
        """Find routes/functions without try/except."""
        issues = []

        for py_file in self.backend_dir.glob("api/*.py"):
            with open(py_file) as f:
                content = f.read()

            # Look for @router patterns without try/except in body
            pattern = r"@router\.(Union[get, post, put]|delete)\([^)]*\)\s*(?:async\s+)?def\s+(\w+)\([^)]*\):[^:]*?(?=@Union[router, def]\s+\w+|$)"
            for match in re.finditer(pattern, content, re.DOTALL):
                func_body = match.group(0)
                if "try:" not in func_body and "async def" in func_body:
                    line_num = content[: match.start()].count("\n") + 1
                    name_match = re.search(r"def\s+(\w+)", func_body)
                    func_name = name_match.group(1) if name_match else "unknown"  # type: ignore[union-attr]
                    issues.append(
                        Issue(
                            severity="HIGH",
                            category="missing_error_handling",
                            file=str(py_file),
                            line=line_num,
                            message=f"Endpoint `{func_name}` has no error handling",
                        )
                    )

        return issues

    def audit_deprecated_code(self) -> list[Issue]:
        """Find deprecated functions or TODO comments."""
        issues = []

        for py_file in self.backend_dir.rglob("*.py"):
            with open(py_file) as f:
                for i, line in enumerate(f, 1):
                    if "deprecated" in line.lower():
                        issues.append(
                            Issue(
                                severity="LOW",
                                category="deprecated_code",
                                file=str(py_file),
                                line=i,
                                message=f"Found deprecation notice: {line.strip()}",
                            )
                        )
                    elif re.match(r"^\s*#\s*TODO", line):
                        issues.append(
                            Issue(
                                severity="LOW",
                                category="todo_item",
                                file=str(py_file),
                                line=i,
                                message=f"TODO: {line.strip()}",
                            )
                        )

        return issues

    def run_full_audit(self) -> list[Issue]:
        """Run all audit checks."""
        print("🔍 Running technical debt audit...")

        self.issues = []
        self.issues.extend(self.audit_broad_exceptions())
        self.issues.extend(self.audit_type_ignore_comments())
        self.issues.extend(self.audit_optional_usage())
        self.issues.extend(self.audit_large_functions())
        self.issues.extend(self.audit_missing_error_handling())
        self.issues.extend(self.audit_deprecated_code())

        return self.issues

    def print_report(self):
        """Print formatted audit report."""
        if not self.issues:
            print("✅ No technical debt issues found!")
            return

        print("\n" + "=" * 80)
        print("TECHNICAL DEBT AUDIT REPORT")
        print("=" * 80)

        # Group by severity
        critical = [i for i in self.issues if i.severity == "CRITICAL"]
        high = [i for i in self.issues if i.severity == "HIGH"]
        medium = [i for i in self.issues if i.severity == "MEDIUM"]
        low = [i for i in self.issues if i.severity == "LOW"]

        for severity_list, severity_name in [
            (critical, "🔴 CRITICAL"),
            (high, "🟠 HIGH"),
            (medium, "🟡 MEDIUM"),
            (low, "🟢 LOW"),
        ]:
            if not severity_list:
                continue

            print(f"\n{severity_name}: {len(severity_list)} issues")
            print("-" * 80)

            for issue in severity_list:
                line_info = f":{issue.line}" if issue.line else ""
                print(f"  {issue.file}{line_info}")
                print(f"    [{issue.category}] {issue.message}")

        print("\n" + "=" * 80)
        print(f"SUMMARY: {len(self.issues)} issues found")
        print(f"  - CRITICAL: {len(critical)}")
        print(f"  - HIGH: {len(high)}")
        print(f"  - MEDIUM: {len(medium)}")
        print(f"  - LOW: {len(low)}")
        print("=" * 80)

    def export_json(self, output_file: Path = Path("ops/technical_debt_audit.json")):
        """Export audit results as JSON."""
        output_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "timestamp": str(Path().cwd()),
            "total_issues": len(self.issues),
            "issues": [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "file": i.file,
                    "line": i.line,
                    "message": i.message,
                }
                for i in self.issues
            ],
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"📊 Audit report exported to {output_file}")


def main():
    import sys

    auditor = TechnicalDebtAuditor(Path("backend"))
    auditor.run_full_audit()
    auditor.print_report()

    if "--export" in sys.argv:
        auditor.export_json()


if __name__ == "__main__":
    main()
