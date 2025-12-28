# Free Intelligence

**Unified CLI-First Development Environment**

This repository uses `fi_cli` as the primary interface for all development and operational tasks. The CLI consolidates 60+ legacy scripts into a single, type-safe, and testable command system.

## 🚀 Quick Start

```bash
# Start development environment
PYTHONPATH=backend/src python -m fi_cli dev all

# Run code quality checks
PYTHONPATH=backend/src python -m fi_cli coder lint-fix

# Deploy to production
PYTHONPATH=backend/src python -m fi_cli deploy setup-backend-service
```

## 📚 Documentation

This repository keeps documentation under `docs/` to keep the root clean.

- Main docs index: `docs/README.md`
- Root index: `docs/README_root.md`
- Assistant system context: `.claude/CLAUDE.md` (folder is gitignored; may not exist on fresh clones)

Quick links:
- Architecture overview: `docs/architecture/aurity_overview.md`
- Technical audit: `docs/TECHNICAL_AUDIT_2025.md`
- Code quality strategy: `docs/CODE_QUALITY_STRATEGY.md`
- CLI reference: `docs/backend/services/cli/README.md`

For more, browse `docs/` categories (architecture, guides, ops, qa, archive, designs, runbooks, tests).

## 🛠️ Why fi_cli?

`fi_cli` is the **recommended interface** for all system operations because:

- **Unified**: Single entry point for 60+ operations across dev, ops, deploy, auth, data, and infra domains
- **Type-safe**: Full type hints and validation prevent errors
- **Testable**: Each command is unit tested and observable
- **Observable**: Built-in metrics and structured logging
- **Secure**: Healthcare-grade security with PHI/PII protection
- **Maintainable**: No more scattered shell scripts

### Migration from Legacy Commands

| Legacy | New fi_cli Command |
|--------|-------------------|
| `make dev-all` | `python -m fi_cli dev all` |
| `make lint` | `python -m fi_cli coder lint-fix` |
| `scripts/dev-start.sh` | `python -m fi_cli dev start` |
| `scripts/deploy-backend.sh` | `python -m fi_cli deploy restart-backend-production` |

## Why fi_cli?

`fi_cli` is the **unified interface** for all system operations because:

### 🔧 **Unified Experience**
- **Single Tool**: One command for 60+ operations across dev, ops, deploy, auth, data, and infra
- **Consistent Interface**: Same command structure and help system everywhere
- **No Script Hunting**: No more searching through `scripts/` directories

### 🛡️ **Healthcare-Grade Quality**
- **Type Safety**: Full type hints and validation prevent runtime errors
- **PHI/PII Protection**: Built-in healthcare data protection in all operations
- **Observable**: Structured logging and metrics for all commands
- **Tested**: Every command has unit tests and integration tests

### 🚀 **Developer Experience**
- **Auto-completion**: Tab completion for all commands and options
- **Help System**: Comprehensive `--help` for every command
- **Error Handling**: Clear error messages with actionable guidance
- **Idempotent**: Safe to run commands multiple times

### 🔄 **Maintainable**
- **Versioned**: Commands evolve with the codebase
- **Documented**: Self-documenting with rich help text
- **Extensible**: Easy to add new commands and domains
- **Reviewed**: All changes go through code review

### 📊 **Observable**
- **Metrics**: Built-in performance and success metrics
- **Logging**: Structured logs with correlation IDs
- **Tracing**: End-to-end operation tracing
- **Monitoring**: Integration with observability systems

**Migration completed December 2025**: All legacy scripts consolidated into fi_cli.

**Note**: `make` commands are kept only for very specific development tasks not covered by fi_cli.
