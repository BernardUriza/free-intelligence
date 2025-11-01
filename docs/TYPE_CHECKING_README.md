# Type Checking Documentation

**Project**: Free Intelligence
**Created**: 2025-10-31
**Purpose**: Automated type checking for Python codebase

---

## Documentation Files

### 📘 [Quick Start Guide](./TYPE_CHECKING_QUICKSTART.md)
**Time to read**: 5 minutes

Essential commands and common fixes for daily development.

**Quick commands**:
```bash
make type-check           # Fast check (pyright)
make type-check-all       # Comprehensive (all tools)
pre-commit run --all-files  # Pre-commit hooks
```

### 📖 [Complete Automation Guide](./TYPE_CHECKING_AUTOMATION_GUIDE.md)
**Time to read**: 30 minutes

Comprehensive guide covering:
- ✅ Pyright, Mypy, Ruff comparison
- ✅ CLI commands and JSON output
- ✅ Pre-commit hooks configuration
- ✅ GitHub Actions CI/CD integration
- ✅ Batch error detection and categorization
- ✅ Claude Code integration for automated fixes
- ✅ SARIF format for GitHub Code Scanning
- ✅ Best practices and troubleshooting

---

## Tool Files

### 🛠️ `/tools/type_check_parsers.py`
Unified JSON parsers for pyright, mypy, and ruff output.

```python
from tools.type_check_parsers import parse_pyright_output

results = parse_pyright_output("pyright_results.json")
for r in results:
    print(f"{r.file}:{r.line} - {r.message}")
```

### 🛠️ `/tools/type_check_batch.py` (To be created)
Batch type checking with error categorization.

```bash
python tools/type_check_batch.py --all --export-sarif --json
```

### 🛠️ `/tools/export_for_claude.py` (To be created)
Export type errors for Claude Code automated fixing.

```bash
python tools/export_for_claude.py --tool pyright --priority critical
```

---

## Configuration Files

### Current Setup

| File | Purpose | Status |
|------|---------|--------|
| `/pyrightconfig.json` | Pyright type checker settings | ✅ Configured |
| `/pyproject.toml` | Mypy + Ruff settings | ✅ Configured |
| `/.pre-commit-config.yaml` | Pre-commit hooks | ✅ Configured |
| `/.github/workflows/quality-gate.yml` | CI/CD quality checks | ✅ Configured |

### Enhancement Opportunities

| File | Purpose | Status |
|------|---------|--------|
| `/.github/workflows/type-safety.yml` | Enhanced type checking CI | 📝 See guide |
| `/.claude/commands/fix-types.md` | Claude Code command | 📝 See guide |

---

## Quick Reference

### Installation
```bash
# Python tools
pip install -e ".[dev]"  # Already includes mypy, ruff

# Pyright (via npm)
npm install -g pyright

# Pre-commit hooks
pre-commit install
```

### Daily Workflow
```bash
# 1. Before coding
git pull

# 2. While coding (VS Code Pylance shows errors automatically)

# 3. Before committing
make type-check  # Quick check

# 4. Commit (pre-commit hooks run automatically)
git commit -m "fix: your changes"

# 5. Before PR (comprehensive check)
make type-check-all
make test
```

### CI/CD
```bash
# Already running in GitHub Actions:
# - MyPy strict type checking (Python 3.11, 3.12)
# - Ruff linting
# - Pre-commit validation
# - Test coverage (80% threshold)
# - Security scanning (Bandit)

# View results:
# https://github.com/BernardUriza/free-intelligence/actions
```

---

## Current Project Status

### Type Coverage
- **68 Python modules** in `/backend`
- **All files** use `from typing import` annotations
- **Type checkers**: Pyright configured, Mypy configured
- **CI/CD**: Quality gate active

### Known Issues
- Some files may have type errors (baseline check recommended)
- Pre-commit mypy runs in isolated venv (dependency awareness limited)
- Strict mode not yet enabled project-wide

### Recommended Next Steps

1. **Baseline Check** (Week 1)
   ```bash
   python tools/type_check_batch.py --all --json
   ```

2. **Fix Critical Errors** (Week 2)
   ```bash
   python tools/export_for_claude.py --tool pyright --priority critical
   # Use Claude Code /fix-types command
   ```

3. **Enable Enhanced CI** (Week 3)
   - Add `.github/workflows/type-safety.yml` (see guide)
   - Enable SARIF upload to GitHub Security

4. **Continuous Improvement** (Ongoing)
   - Weekly type check reports
   - Strict mode for new code
   - Developer training

---

## Healthcare-Grade Type Safety

**Why it matters**:
- ✅ Medical data must be type-safe
- ✅ Errors can have serious consequences
- ✅ Regulatory compliance requires code quality
- ✅ Type hints improve code documentation
- ✅ Easier onboarding for new developers

**Critical type rules enforced**:
- `reportArgumentType`: Wrong argument types
- `reportAssignmentType`: Wrong assignment types
- `reportOptionalMemberAccess`: Accessing None values
- `reportGeneralTypeIssues`: General type errors

See `pyrightconfig.json` for complete configuration.

---

## Integration with Development Workflow

### VS Code (Pylance)
Type checking is **automatic** with Pylance extension:
- Red squiggles show type errors in real-time
- Hover for detailed explanations
- Quick fixes available (💡 icon)

Configuration: `pyrightconfig.json` (already set up)

### Pre-commit Hooks
Type checking runs **automatically** on commit:
- Ruff: Fast linting and formatting
- MyPy: Strict type checking
- Bandit: Security scanning

Configuration: `.pre-commit-config.yaml` (already set up)

### GitHub Actions
Type checking runs **automatically** on push/PR:
- Multiple Python versions (3.11, 3.12)
- Comprehensive checks (MyPy + Ruff)
- Coverage requirements (80%+)
- Security audit

Configuration: `.github/workflows/quality-gate.yml` (already set up)

### Claude Code
Type error fixing **semi-automated**:
- Export errors to JSON
- Claude processes in batches
- Systematic verification
- Automated commits

Configuration: See [Complete Guide](./TYPE_CHECKING_AUTOMATION_GUIDE.md#claude-code-integration)

---

## Tools Comparison

| Tool | Speed | Coverage | Use Case |
|------|-------|----------|----------|
| **Pyright** | ⚡⚡⚡ Fastest | Good | Quick local checks, CI/CD |
| **Mypy** | ⚡⚡ Medium | Excellent | Comprehensive checking |
| **Ruff** | ⚡⚡⚡ Fastest | Linting only | Code style, unused imports |

**Recommendation**: Use all three
- Pyright for fast feedback
- Mypy for thorough checks
- Ruff for code style

---

## Output Formats

All tools support **JSON output** for automation:

```bash
# Pyright
pyright backend/ --outputjson > pyright.json

# Mypy
mypy backend/ --output=json > mypy.json

# Ruff
ruff check backend/ --output-format=json > ruff.json
```

**SARIF format** (GitHub Code Scanning):
```bash
python tools/type_check_batch.py --all --export-sarif
```

---

## Getting Help

| Question | Resource |
|----------|----------|
| Quick command? | [Quick Start Guide](./TYPE_CHECKING_QUICKSTART.md) |
| How does it work? | [Complete Guide](./TYPE_CHECKING_AUTOMATION_GUIDE.md) |
| Common errors? | [Complete Guide - Common Fixes](./TYPE_CHECKING_AUTOMATION_GUIDE.md#common-fixes) |
| CI/CD failing? | [Complete Guide - Troubleshooting](./TYPE_CHECKING_AUTOMATION_GUIDE.md#troubleshooting) |
| Claude Code integration? | [Complete Guide - Claude Code](./TYPE_CHECKING_AUTOMATION_GUIDE.md#claude-code-integration) |

---

## File Summary

**Created files**:
1. `/docs/TYPE_CHECKING_README.md` (this file) - Overview and index
2. `/docs/TYPE_CHECKING_QUICKSTART.md` - 5-minute quick start
3. `/docs/TYPE_CHECKING_AUTOMATION_GUIDE.md` - Complete 30-minute guide
4. `/tools/type_check_parsers.py` - JSON parsers for all tools

**Referenced files** (templates in guide):
5. `/tools/type_check_batch.py` - Batch checking script
6. `/tools/export_for_claude.py` - Claude Code export script
7. `/.github/workflows/type-safety.yml` - Enhanced CI workflow
8. `/.claude/commands/fix-types.md` - Claude Code command

**Existing files** (already configured):
- `/pyrightconfig.json` - Pyright configuration
- `/pyproject.toml` - Mypy + Ruff configuration
- `/.pre-commit-config.yaml` - Pre-commit hooks
- `/.github/workflows/quality-gate.yml` - Current CI/CD
- `/Makefile` - Build commands

---

**Last updated**: 2025-10-31
**Maintainer**: Bernard Uriza Orozco
**Project**: Free Intelligence v0.3.0
