# Type Checking Quick Start

## 🚀 How Professional Python Teams Use Type Checking with Pylance

### Installation (One-time)

```bash
# Install Pyright CLI (powers Pylance)
npm install -g pyright

# Or use pip
pip install pyright

# Verify installation
pyright --version
```

### Daily Workflow

#### 1. Quick Type Check (2 seconds)
```bash
# Run Pyright directly (fastest)
pyright backend/

# Or use Makefile
make type-check
```

#### 2. Comprehensive Check (15 seconds)
```bash
# Run all type checkers
make type-check-all

# Or manually
pyright backend/ && mypy backend/ --ignore-missing-imports && ruff check backend/
```

#### 3. Export Errors for Claude Code
```bash
# Export results as JSON
make type-check-export

# Or export all checkers
make type-check-batch
```

### Common CLI Commands

#### Pyright (Fast, CLI-based)
```bash
# Basic check
pyright backend/

# JSON output (for automation)
pyright backend/ --outputjson > diagnostics.json

# Watch mode (auto-check on file change)
pyright --watch backend/

# Specific Python version
pyright --pythonversion 3.11 backend/
```

#### Mypy (Thorough)
```bash
# Basic check
mypy backend/ --ignore-missing-imports

# Show error codes
mypy backend/ --show-error-codes

# Strict mode (recommended for production)
mypy backend/ --strict

# JSON output
mypy backend/ --output=json > results.json
```

#### Ruff (Linting only, not type checking)
```bash
# Check for linting issues
ruff check backend/

# Auto-fix issues
ruff check backend/ --fix

# Format code
ruff format backend/
```

### Automation with Makefile

All commands are available via Makefile:

```bash
# Quick check (2 sec)
make type-check

# Mypy check (5-10 sec)
make type-check-mypy

# All tools (15 sec)
make type-check-all

# Export as JSON (for batch processing)
make type-check-export

# Full batch check with all tools
make type-check-batch
```

### Quick Reference

| Task | Command | Time | When to Use |
|------|---------|------|------------|
| Quick check | `make type-check` | 2 sec | Local dev, before commit |
| Thorough check | `make type-check-mypy` | 5-10 sec | Before PR |
| All tools | `make type-check-all` | 15 sec | CI/CD, comprehensive review |
| Export JSON | `make type-check-export` | 3 sec | Claude Code batch fixing |
| Full batch | `make type-check-batch` | 20 sec | Large-scale error fixing |

### Key Commands for Your Project

```bash
# Quick check with Pyright (what you need right now)
make type-check

# See all errors categorized
make type-check-batch

# Use with Claude Code for batch fixing
make type-check-export && cat ops/type_check_results/results.json | jq '.summary'
```

---

**Key Insight**: Professional teams use **Pyright CLI** (same engine as Pylance) for:
- Fast local feedback
- Automation in CI/CD
- JSON exports for tooling
- Batch error processing
