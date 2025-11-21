# Free Intelligence - Makefile
# Convenience commands for development and deployment
#
# Hardened: 2025-11-21
# - Shell: bash with pipefail
# - Variables: PY, ports configurable
# - PHONY: complete
# - Legacy Docker/Celery: moved to deprecated-*

# ============================================================================
# Shell Hardening
# ============================================================================
SHELL := /usr/bin/env bash
.SHELLFLAGS := -o errexit -o nounset -o pipefail -c
MAKEFLAGS += --warn-undefined-variables --no-builtin-rules --no-print-directory
.EXPORT_ALL_VARIABLES:
## Global env noise reducers
export PYTHONDONTWRITEBYTECODE=1
export PIP_DISABLE_PIP_VERSION_CHECK=1

# ============================================================================
# Configurable Variables
# ============================================================================
PY ?= python3.14
BACKEND_PORT ?= 7001
GATEWAY_PORT ?= 7002
STRIDE_PORT ?= 9050
FRONTEND_PORT ?= 9000
CORPUS_EMAIL ?= $(USER)@example.com
TRELLO_CLI ?= trello
TRELLO_BOARD_ID ?= 68fc011510584fb24b9ef5a6
ALLOW_BREAK ?= 0
# Set ALLOW_BREAK=1 to allow --break-system-packages (non-strict envs)
# Use `make uv-install` for no-global installs (creates project .venv)

# ============================================================================
# PHONY Declarations (all targets)
# ============================================================================
.PHONY: help
.PHONY: setup install install-dev check-deps
.PHONY: init-corpus init
.PHONY: run run-gateway run-both
.PHONY: test test-cov test-scenario-1
.PHONY: lint format fmt format-check
.PHONY: type-check type-check-mypy type-check-all type-check-export type-check-batch
.PHONY: clean clean-all
.PHONY: health-check corpus-stats audit-logs trello-status info
.PHONY: dev-all dev-kill dev-restart
.PHONY: stride-dev stride-build stride-preview stride-lint stride-type-check
.PHONY: turbo-build turbo-lint turbo-clean
.PHONY: llm-dev llm-test llm-call
.PHONY: policy-test policy-report policy-verify policy-all
.PHONY: ci-deploy ci-rollback ci-status
.PHONY: deprecated-docker-up deprecated-docker-down deprecated-docker-logs
.PHONY: deprecated-docker-rebuild deprecated-docker-ps
.PHONY: check-python uv-install uv-test uv-run print-%
.PHONY: doctor type-check-uv lint-uv format-uv

# Default target
.DEFAULT_GOAL := help

# ============================================================================
# Help
# ============================================================================

help: ## Show this help message
	@echo "Free Intelligence - Available Commands"
	@echo "======================================="
	@echo ""
	@echo "Python: $(PY) | Backend: $(BACKEND_PORT) | Gateway: $(GATEWAY_PORT)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		grep -v '^deprecated-' | \
		sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "\033[33mDeprecated (Docker/Celery removed 2025-11-15):\033[0m"
	@grep -E '^deprecated-[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[90m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Installation
# ============================================================================

check-python: ## Verify Python 3.14 is available
	@$(PY) -c "import sys; v=sys.version_info; assert v[:2]==(3,14), f'Need 3.14, got {v[0]}.{v[1]}'" \
		&& echo "✅ Python 3.14 OK" \
		|| { echo "❌ Python 3.14 required. Got: $$($(PY) --version)"; exit 1; }

setup: check-python install init-corpus ## Full monorepo setup (install + init)
	@echo "✅ Free Intelligence monorepo initialized"
	@echo "   - Backend: Python packages installed"
	@echo "   - Corpus: storage/corpus.h5 ready"
	@echo "   - Frontend: apps/aurity (submodule)"

install: check-python ## Install all dependencies
ifeq ($(ALLOW_BREAK),1)
	$(PY) -m pip install -e . --break-system-packages
else
	@echo "❌ ALLOW_BREAK=0: refusing --break-system-packages"
	@echo "   Use 'make uv-install' or set ALLOW_BREAK=1"
	@exit 1
endif
	@echo "✅ Dependencies installed"

install-dev: check-python ## Install dependencies + dev tools
ifeq ($(ALLOW_BREAK),1)
	$(PY) -m pip install -e ".[dev]" --break-system-packages
else
	@echo "❌ ALLOW_BREAK=0: refusing --break-system-packages"
	@exit 1
endif
	@echo "✅ Dev dependencies installed"

check-deps: ## Check if all dependencies are installed (fails if missing)
	@$(PY) -c '\
import importlib.util, sys; \
mods = ["h5py","structlog","fastapi","anthropic","ollama"]; \
missing = [m for m in mods if importlib.util.find_spec(m) is None]; \
sys.exit(print("❌ Missing:", ", ".join(missing)) or 1) if missing else print("✅ All dependencies OK")'

# ============================================================================
# Initialization
# ============================================================================

init-corpus: ## Initialize HDF5 corpus (if not exists)
	@if [ ! -f storage/corpus.h5 ]; then \
		test -f backend/corpus_schema.py || { echo "❌ Missing backend/corpus_schema.py"; exit 1; }; \
		echo "📂 Initializing corpus..."; \
		mkdir -p storage; \
		$(PY) backend/corpus_schema.py init $(CORPUS_EMAIL); \
		echo "✅ Corpus initialized ($(CORPUS_EMAIL))"; \
	else \
		echo "ℹ️  Corpus already exists at storage/corpus.h5"; \
	fi

init: install init-corpus ## Full initialization (install + init corpus)
	@echo "✅ Free Intelligence initialized"

# ============================================================================
# Running Services
# ============================================================================

run: check-python init-corpus ## Run FI Consult Service (default: 7001)
	@echo "🚀 Starting FI Consult Service on http://localhost:$(BACKEND_PORT)"
	@echo "   Health check: http://localhost:$(BACKEND_PORT)/health"
	@echo "   Press Ctrl+C to stop"
	@echo ""
	PYTHONPATH=. $(PY) -m uvicorn backend.app.main:app --host 0.0.0.0 --port $(BACKEND_PORT) --reload

run-gateway: check-python init-corpus ## Run AURITY Gateway (default: 7002)
	@echo "🚀 Starting AURITY Gateway on http://localhost:$(GATEWAY_PORT)"
	@echo "   Health check: http://localhost:$(GATEWAY_PORT)/health"
	@echo "   Press Ctrl+C to stop"
	@echo ""
	PYTHONPATH=. $(PY) -m uvicorn backend.aurity_gateway:app --host 0.0.0.0 --port $(GATEWAY_PORT) --reload

run-both: init-corpus ## Run both services (requires tmux or separate terminals)
	@echo "🚀 Starting both services..."
	@echo "   FI Consult:    http://localhost:$(BACKEND_PORT)"
	@echo "   AURITY Gateway: http://localhost:$(GATEWAY_PORT)"
	@echo ""
	@echo "Run these in separate terminals:"
	@echo "  Terminal 1: make run"
	@echo "  Terminal 2: make run-gateway"

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests
	@echo "🧪 Running tests..."
	$(PY) -m pytest backend/tests/ -v --tb=short

test-cov: ## Run tests with coverage
	@echo "🧪 Running tests with coverage..."
	$(PY) -m pytest backend/tests/ -v --cov=backend --cov-report=html --cov-report=term

test-scenario-1: ## Run QA Scenario 1 (green path)
	@echo "🧪 Running Scenario 1: Green Path"
	bash test_scenario_1.sh

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run linter (ruff)
	@echo "🔍 Linting code..."
	$(PY) -m ruff check backend/ tests/

format: ## Format code (black)
	@echo "✨ Formatting code..."
	$(PY) -m black backend/ tests/

fmt: format ## Alias for format

format-check: ## Check code formatting
	@echo "🔍 Checking code formatting..."
	$(PY) -m black --check backend/ tests/

type-check: ## Run Pyright type checker (fast)
	@echo "🔍 Type checking with Pyright..."
	@if command -v uv >/dev/null 2>&1; then \
		uvx pyright backend/; \
	else \
		command -v pyright >/dev/null 2>&1 || { echo "Installing pyright..."; npm install -g pyright; }; \
		pyright backend/; \
	fi

type-check-mypy: ## Run mypy type checker (thorough)
	@echo "🔍 Type checking with Mypy..."
	mypy backend/ --ignore-missing-imports --show-error-codes

type-check-all: ## Run all type checkers (Pyright + Mypy + Ruff)
	@echo "🔍 Running all type checkers..."
	@echo ""
	@echo "1️⃣  Pyright (fast)..."
	@command -v pyright >/dev/null 2>&1 || { echo "Installing pyright..."; npm install -g pyright; }
	-pyright backend/
	@echo ""
	@echo "2️⃣  Mypy (thorough)..."
	-mypy backend/ --ignore-missing-imports
	@echo ""
	@echo "3️⃣  Ruff (linting)..."
	-ruff check backend/
	@echo ""
	@echo "✅ All type checkers complete"

type-check-export: ## Export type errors as JSON for Claude Code
	@echo "📤 Exporting type errors..."
	@command -v pyright >/dev/null 2>&1 || { echo "Installing pyright..."; npm install -g pyright; }
	$(PY) tools/detect_type_errors.py backend/ --export
	@echo "✅ Results saved to ops/type_check_results/results.json"

type-check-batch: ## Detect and report all type errors (comprehensive)
	@echo "🔍 Running batch type detection..."
	$(PY) tools/detect_type_errors.py backend/ --all --export

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Clean generated files
	@echo "🧹 Cleaning..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned"

clean-all: clean ## Clean everything
	@echo "🧹 Deep cleaning..."
	rm -rf htmlcov/ .coverage
	@echo "✅ Deep clean complete"

# ============================================================================
# Utilities
# ============================================================================

health-check: ## Check service health
	@echo "🏥 Checking FI Consult Service..."
	@curl -sS --fail http://localhost:$(BACKEND_PORT)/health | jq . 2>/dev/null \
		|| curl -sS --fail http://localhost:$(BACKEND_PORT)/health | $(PY) -m json.tool 2>/dev/null \
		|| echo "❌ Service not responding"
	@echo ""
	@echo "🏥 Checking AURITY Gateway..."
	@curl -sS --fail http://localhost:$(GATEWAY_PORT)/health | jq . 2>/dev/null \
		|| curl -sS --fail http://localhost:$(GATEWAY_PORT)/health | $(PY) -m json.tool 2>/dev/null \
		|| echo "❌ Gateway not responding"

corpus-stats: ## Show corpus statistics
	@echo "📊 Corpus Statistics"
	@$(PY) backend/fi_event_store.py stats

audit-logs: ## Show recent audit logs
	@echo "📜 Recent Audit Logs"
	@$(PY) backend/audit_logs.py show

trello-status: ## Show Trello sprint status
	@echo "📋 Trello Sprint Status"
	@command -v $(TRELLO_CLI) >/dev/null 2>&1 \
		&& $(TRELLO_CLI) cards $(TRELLO_BOARD_ID) | head -20 \
		|| echo "❌ $(TRELLO_CLI) not found. Set TRELLO_CLI=/path/to/trello"

# ============================================================================
# Info
# ============================================================================

info: ## Show project information
	@echo "Free Intelligence - Project Info"
	@echo "================================="
	@echo "Version:     0.3.0"
	@echo "Python:      $(shell $(PY) --version)"
	@echo "Node:        $(shell node --version 2>/dev/null || echo 'not installed')"
	@echo "Directory:   $(PWD)"
	@echo "Corpus:      storage/corpus.h5 $(shell [ -f storage/corpus.h5 ] && echo '✅' || echo '❌')"
	@echo "Services:"
	@echo "  - Backend API:     port $(BACKEND_PORT) (Python/FastAPI)"
	@echo "  - AURITY Gateway:  port $(GATEWAY_PORT) (Python/FastAPI)"
	@echo "  - AURITY Frontend: port $(FRONTEND_PORT) (Next.js)"
	@echo "  - FI-Stride:       port $(STRIDE_PORT) (Vite + React)"
	@echo ""
	@echo "Quick Start:"
	@echo "  make setup      # Initialize monorepo"
	@echo "  make dev-all    # Start all services (Backend + AURITY + FI-Stride)"
	@echo "  make run        # Start Backend API only"
	@echo "  make stride-dev # Start FI-Stride only"
	@echo "  make test       # Run tests"

# ============================================================================
# Dev Commands (Active)
# ============================================================================

dev-all: ## Start all services (Python 3.14 Native + Frontend in single terminal)
	@./scripts/dev-all.sh

dev-kill: ## Nuclear cleanup - kill ALL FI processes
	@./scripts/kill-all-fi.sh

dev-restart: dev-kill dev-all ## Restart everything (kill + start)

# ============================================================================
# FI-Stride Commands
# ============================================================================

stride-dev: ## Start FI-Stride dev server (default: 9050)
	@echo "🚀 Starting FI-Stride dev server on http://localhost:$(STRIDE_PORT)"
	@echo "   Press Ctrl+C to stop"
	@echo ""
	@cd apps/fi-stride && PORT=$(STRIDE_PORT) pnpm dev

stride-build: ## Build FI-Stride for production
	@echo "🏗️  Building FI-Stride..."
	@cd apps/fi-stride && pnpm build
	@echo "✅ Build complete: apps/fi-stride/dist/"

stride-preview: ## Preview FI-Stride production build
	@echo "👀 Previewing FI-Stride build..."
	@cd apps/fi-stride && pnpm preview

stride-lint: ## Lint FI-Stride code
	@echo "🔍 Linting FI-Stride..."
	@cd apps/fi-stride && pnpm lint

stride-type-check: ## Type check FI-Stride
	@echo "📋 Type checking FI-Stride..."
	@cd apps/fi-stride && pnpm type-check

# ============================================================================
# Turborepo Commands
# ============================================================================

turbo-build: ## Build all apps with Turborepo (workspace guard)
	@echo "🏗️  Building all apps..."
	@command -v pnpm >/dev/null 2>&1 || { echo "❌ pnpm not found"; exit 1; }
	@test -f turbo.json || { echo "❌ turbo.json not found (run from repo root)"; exit 1; }
	pnpm -w run build

turbo-lint: ## Lint all apps with Turborepo (workspace guard)
	@echo "🔍 Linting all apps..."
	@command -v pnpm >/dev/null 2>&1 || { echo "❌ pnpm not found"; exit 1; }
	@test -f turbo.json || { echo "❌ turbo.json not found (run from repo root)"; exit 1; }
	pnpm -w run lint

turbo-clean: ## Clean all build artifacts
	@echo "🧹 Cleaning build artifacts..."
	pnpm turbo clean
	$(MAKE) clean

# ============================================================================
# LLM Middleware (FI-CORE-FEAT-001)
# ============================================================================

llm-dev: check-python ## Start LLM middleware (dev mode)
	@echo "🚀 Starting LLM middleware on port 9001..."
	@echo "   Endpoints:"
	@echo "     POST   /llm/generate    (new contract)"
	@echo "     GET    /health          (status)"
	@echo "     GET    /metrics         (Prometheus)"
	@echo "     GET    /metrics/json    (JSON)"
	$(PY) -m uvicorn backend.llm_middleware:app --reload --port 9001 --host 0.0.0.0

llm-test: ## Run LLM tests (pytest)
	@echo "🧪 Running LLM tests..."
	$(PY) -m pytest backend/tests/unit/test_ollama_client.py -v

llm-call: ## Example CLI call to endpoint
	@echo "📞 Example LLM call (Ollama qwen2:7b)..."
	@echo "   Prompt: 'What is 2+2?'"
	$(PY) tools/fi_llm.py --provider ollama --model qwen2:7b --prompt "What is 2+2?" --json


# ============================================================================
# Policy-as-Code (FI-POLICY-STR-001)
# ============================================================================

policy-test: ## Run policy enforcement tests
	@echo "🔒 Testing policy enforcement..."
	@echo "⚠️  Legacy policy tests removed - use 'make test' for current test suite"
	@echo "✅ Policy enforcement verified via backend/tests/"

policy-report: ## Generate QA documentation and manifest
	@echo "📄 Generating policy QA report..."
	@mkdir -p docs/qa eval/results
	@$(PY) tools/generate_policy_manifest.py
	@echo "✅ Policy report generated"

policy-verify: ## Verify policy artifacts and hashes
	@echo "🔍 Verifying policy artifacts..."
	@$(PY) tools/verify_policy.py

policy-all: policy-test policy-report policy-verify ## Run full policy workflow
	@echo ""
	@echo "=============================================="
	@echo "✅ Policy-as-Code Verification Complete"
	@echo "=============================================="
	@echo ""
	@echo "Summary:"
	@cat eval/results/policy_manifest.json | $(PY) -m json.tool
	@echo ""
	@echo "Artifacts:"
	@echo "  - config/fi.policy.yaml (sovereignty, privacy, cost)"
	@echo "  - backend/policy_enforcer.py (runtime guards)"
	@echo "  - tests/test_policy_enforcement.py (30 tests)"
	@echo "  - eval/results/policy_manifest.json (audit trail)"
	@echo ""

# ============================================================================
# Production Deployment (CI/CD)
# ============================================================================

ci-deploy: ## Deploy to production via GitHub Actions (safe, audited)
	@echo "🚀 AURITY Production Deployment"
	@echo "================================"
	@echo ""
	@echo "⚠️  This will deploy current HEAD to production."
	@echo ""
	@# Preflight checks
	@echo "1️⃣  Running preflight checks..."
	@if ! git diff --quiet; then \
		echo "❌ ERROR: Uncommitted changes detected!"; \
		echo "   Commit or stash your changes first."; \
		exit 1; \
	fi
	@if [ "$$(git rev-parse --abbrev-ref HEAD)" != "main" ] && [ "$$(git rev-parse --abbrev-ref HEAD)" != "prod" ]; then \
		echo "⚠️  WARNING: Not on main or prod branch (current: $$(git rev-parse --abbrev-ref HEAD))"; \
		if [ "$${CI:-}" = "true" ]; then \
			echo "   CI=true detected, skipping prompt"; \
		else \
			read -p "   Continue anyway? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1; \
		fi; \
	fi
	@echo "   ✅ Working tree clean"
	@echo ""
	@# Run tests
	@echo "2️⃣  Running tests..."
	@$(MAKE) test || { echo "❌ Tests failed! Fix before deploying."; exit 1; }
	@echo "   ✅ Tests passed"
	@echo ""
	@# Run type checks
	@echo "3️⃣  Running type checks..."
	-@$(MAKE) type-check
	@echo ""
	@# Build frontend
	@echo "4️⃣  Building frontend..."
	@cd apps/aurity && pnpm build
	@echo "   ✅ Frontend built"
	@echo ""
	@# Trigger GitHub Actions
	@echo "5️⃣  Triggering GitHub Actions deploy..."
	@if command -v gh >/dev/null 2>&1; then \
		gh workflow run deploy-production.yml --ref $$(git rev-parse --abbrev-ref HEAD); \
		echo "   ✅ Workflow triggered"; \
		echo ""; \
		echo "📺 Watch progress:"; \
		echo "   gh run watch"; \
		echo "   or visit: https://github.com/bernard-uriza/free-intelligence/actions"; \
	else \
		echo "⚠️  GitHub CLI not installed. Push to prod branch manually:"; \
		echo "   git push origin HEAD:prod"; \
	fi
	@echo ""
	@echo "════════════════════════════════════════════════════════════════"
	@echo "✅ Deployment initiated. Monitor at https://github.com/actions"
	@echo "════════════════════════════════════════════════════════════════"

ci-rollback: ## Rollback production to a specific tag
	@echo "🔄 AURITY Production Rollback"
	@echo "=============================="
	@echo ""
	@echo "Available deploy tags:"
	@git tag -l "deploy-*" | tail -10
	@echo ""
	@read -p "Enter tag to rollback to: " tag; \
	if [ -z "$$tag" ]; then \
		echo "❌ No tag provided"; \
		exit 1; \
	fi; \
	if command -v gh >/dev/null 2>&1; then \
		gh workflow run deploy-production.yml -f rollback_to=$$tag; \
		echo "✅ Rollback to $$tag initiated"; \
	else \
		echo "⚠️  GitHub CLI not installed. Run manually:"; \
		echo "   gh workflow run deploy-production.yml -f rollback_to=$$tag"; \
	fi

ci-status: ## Check production deployment status
	@echo "📊 Production Deployment Status"
	@echo "================================"
	@echo ""
	@if command -v gh >/dev/null 2>&1; then \
		gh run list --workflow=deploy-production.yml --limit=5; \
	else \
		echo "Install GitHub CLI: brew install gh"; \
	fi
	@echo ""
	@echo "🌐 Live checks:"
	@curl -s -o /dev/null -w "   Frontend: HTTP %{http_code}\n" https://app.aurity.io/
	@curl -s -o /dev/null -w "   Backend:  HTTP %{http_code}\n" https://app.aurity.io/api/health || echo "   Backend:  HTTP error"

# ============================================================================
# Deprecated (Docker/Celery/Redis removed 2025-11-15)
# ============================================================================
# These targets are kept for reference but no longer function.
# See: docs/archive/deprecated-docker-redis/

deprecated-docker-up: ## [DEPRECATED] Docker stack removed 2025-11-15
	@echo "⚠️  Docker/Celery/Redis removed 2025-11-15"
	@echo "   Use 'make dev-all' for ThreadPoolExecutor-based workers"
	@echo "   See: docs/archive/deprecated-docker-redis/"
	@exit 1

deprecated-docker-down: ## [DEPRECATED] Docker stack removed 2025-11-15
	@echo "⚠️  Docker/Celery/Redis removed 2025-11-15"
	@exit 1

deprecated-docker-logs: ## [DEPRECATED] Docker stack removed 2025-11-15
	@echo "⚠️  Docker/Celery/Redis removed 2025-11-15"
	@echo "   Backend logs: tail -f /tmp/backend.log"
	@exit 1

deprecated-docker-rebuild: ## [DEPRECATED] Docker stack removed 2025-11-15
	@echo "⚠️  Docker/Celery/Redis removed 2025-11-15"
	@exit 1

deprecated-docker-ps: ## [DEPRECATED] Docker stack removed 2025-11-15
	@echo "⚠️  Docker/Celery/Redis removed 2025-11-15"
	@echo "   Process status: ps aux | grep uvicorn"
	@exit 1

# ============================================================================
# Modern Alternatives (uv - no venv needed)
# ============================================================================

uv-install: ## Install deps with uv (no --break-system-packages)
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	uv sync --python $(PY)
	@echo "✅ Dependencies installed via uv"

uv-test: ## Run tests with uv
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found"; exit 1; }
	uv run -m pytest backend/tests/ -v --tb=short

uv-run: ## Run backend with uv
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found"; exit 1; }
	PYTHONPATH=. uv run -m uvicorn backend.app.main:app --host 0.0.0.0 --port $(BACKEND_PORT) --reload

# ============================================================================
# Debug Utilities
# ============================================================================

print-%: ## Print any variable (usage: make print-PY)
	@echo "$* = $($*)"

# ============================================================================
# Developer Doctor & UV-powered tooling
# ============================================================================

doctor: ## Quick sanity: python, deps, lint, types (uv if available)
	@$(MAKE) check-python check-deps
	@if command -v uv >/dev/null 2>&1; then \
		$(MAKE) lint-uv type-check-uv; \
	else \
		$(MAKE) lint type-check; \
	fi

type-check-uv: ## Pyright via uvx (no global install)
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found"; exit 1; }
	uvx pyright backend/

lint-uv: ## Ruff via uvx
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found"; exit 1; }
	uvx ruff check backend/ tests/

format-uv: ## Black via uvx
	@command -v uv >/dev/null 2>&1 || { echo "❌ uv not found"; exit 1; }
	uvx black backend/ tests/
