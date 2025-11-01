# Type Checking Cheat Sheet

Quick reference for daily development.

## Installation

```bash
# Python tools (already in requirements)
pip install -e ".[dev]"

# Pyright (fastest)
npm install -g pyright

# Pre-commit hooks
pre-commit install
```

## Daily Commands

```bash
# Quick check (Pyright - fastest)
make type-check
pyright backend/

# Comprehensive check
make type-check-all
pyright backend/ && mypy backend/ && ruff check backend/

# Fix auto-fixable issues
ruff check backend/ --fix

# Pre-commit hooks
pre-commit run --all-files
```

## JSON Output (Automation)

```bash
# Pyright
pyright backend/ --outputjson > pyright.json

# Mypy
mypy backend/ --output=json > mypy.json

# Ruff
ruff check backend/ --output-format=json > ruff.json
```

## Parse Results

```python
from tools.type_check_parsers import parse_pyright_output

results = parse_pyright_output("pyright.json")
errors = [r for r in results if r.severity == "error"]
print(f"Found {len(errors)} errors")
```

## Common Fixes

### Add type hints
```python
# Before
def process(data):
    return data.upper()

# After
def process(data: str) -> str:
    return data.upper()
```

### Handle Optional
```python
# Before
def get_user(id: int) -> User:
    return db.get(id)  # ❌ Might be None

# After
from typing import Optional

def get_user(id: int) -> Optional[User]:
    return db.get(id)
```

### Type narrowing
```python
# Before
def process(value: str | None):
    return value.upper()  # ❌ Error

# After
def process(value: str | None):
    if value is None:
        return None
    return value.upper()  # ✅ OK
```

## Ignore Errors (Last Resort)

```python
# Pyright
x = some_func()  # type: ignore[reportArgumentType]

# Mypy
x = some_func()  # type: ignore[arg-type]
```

## CI/CD

```bash
# Already running in GitHub Actions
# View: https://github.com/[org]/free-intelligence/actions

# Local CI simulation
python tools/type_check_batch.py --all --json
```

## Batch Fixing

```bash
# Export for Claude Code
python tools/export_for_claude.py --tool pyright --priority critical

# Review
cat ops/claude_fix_tasks.json | jq '.stats'

# Use Claude Code /fix-types command
```

## Configuration Files

| File | Purpose |
|------|---------|
| `/pyrightconfig.json` | Pyright settings |
| `/pyproject.toml` | Mypy + Ruff |
| `/.pre-commit-config.yaml` | Hooks |

## Troubleshooting

```bash
# Clear caches
rm -rf .mypy_cache node_modules/.cache/pyright

# Verbose output
pyright backend/ --verbose
mypy backend/ --verbose

# Check single file
pyright backend/llm_router.py
mypy backend/llm_router.py
```

## Documentation

- **Quick Start**: [TYPE_CHECKING_QUICKSTART.md](./TYPE_CHECKING_QUICKSTART.md)
- **Complete Guide**: [TYPE_CHECKING_AUTOMATION_GUIDE.md](./TYPE_CHECKING_AUTOMATION_GUIDE.md)
- **Overview**: [TYPE_CHECKING_README.md](./TYPE_CHECKING_README.md)

---

**Project**: Free Intelligence v0.3.0
**Last updated**: 2025-10-31
