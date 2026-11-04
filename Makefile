# Free Intelligence - Makefile
# Local commands for the apps that ship: og118 (web + server) and the fi-core
# RAG smoke. CI/CD lives in .github/workflows; nothing here deploys.

SHELL := /usr/bin/env bash
.SHELLFLAGS := -o errexit -o nounset -o pipefail -c
MAKEFLAGS += --warn-undefined-variables --no-builtin-rules --no-print-directory
.EXPORT_ALL_VARIABLES:
export PYTHONDONTWRITEBYTECODE=1
export PIP_DISABLE_PIP_VERSION_CHECK=1

PY ?= python3.14
OG118_SERVER_DIR ?= apps/og118/server
OG118_SERVER_PORT ?= 8118
OG118_WEB_PORT ?= 3000

FI_RAG_PG_CONTAINER ?= fi-rag-smoke
FI_RAG_PG_PORT ?= 5433
FI_RAG_PG_PASSWORD ?= smoke
FI_RAG_PG_DB ?= firag
FI_RAG_PG_IMAGE ?= pgvector/pgvector:pg16
FI_RAG_PGVECTOR_TEST_DSN ?= postgresql://postgres:$(FI_RAG_PG_PASSWORD)@localhost:$(FI_RAG_PG_PORT)/$(FI_RAG_PG_DB)

.PHONY: help dev dev-server dev-web dev-kill test test-server test-web
.PHONY: test-rag-smoke test-rag-smoke-down turbo-build turbo-lint turbo-clean
.PHONY: clean clean-all print-%

.DEFAULT_GOAL := help

help: ## Show this help message
	@grep -E '^[a-zA-Z_%-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# og118 (the app that ships: app.og118.ai)
# ============================================================================

dev: ## Start og118 server (:8118) + web (:3000) together; Ctrl-C stops both
	$(MAKE) -j2 dev-server dev-web

dev-server: ## Start the og118 FastAPI server via its run.sh (needs .venv + .env.local)
	@test -d $(OG118_SERVER_DIR)/.venv || { echo "missing $(OG118_SERVER_DIR)/.venv: see $(OG118_SERVER_DIR)/README.md"; exit 1; }
	$(OG118_SERVER_DIR)/run.sh

dev-web: ## Start the og118 web app (next dev, auth0 mode from .env.local)
	pnpm --filter og118-web dev

dev-kill: ## Stop whatever listens on the og118 server and web ports
	@for port in $(OG118_SERVER_PORT) $(OG118_WEB_PORT); do \
		pids=$$(lsof -ti tcp:$$port -sTCP:LISTEN || true); \
		if [ -n "$$pids" ]; then kill $$pids && echo "stopped :$$port ($$pids)"; else echo ":$$port free"; fi; \
	done

test: test-server test-web ## Run the og118 server (pytest) and web (vitest) suites

test-server: ## Run the og118 server suite with its .venv
	cd $(OG118_SERVER_DIR) && .venv/bin/python -m pytest tests -q

test-web: ## Run the og118 web suite (vitest)
	pnpm --filter og118-web test

# ============================================================================
# fi-core RAG smoke
# ============================================================================

test-rag-smoke: ## Run fi-core RAG smoke vs a REAL pgvector DB (auto-starts a throwaway container)
	@echo "🧪 RAG pgvector smoke → container '$(FI_RAG_PG_CONTAINER)' on :$(FI_RAG_PG_PORT)"
	@if [ -n "$$(docker ps -q -f name=^/$(FI_RAG_PG_CONTAINER)$$)" ]; then \
		echo "  ↳ reusing running container"; \
	elif [ -n "$$(docker ps -aq -f name=^/$(FI_RAG_PG_CONTAINER)$$)" ]; then \
		echo "  ↳ starting existing container"; docker start $(FI_RAG_PG_CONTAINER) >/dev/null; \
	else \
		echo "  ↳ creating container ($(FI_RAG_PG_IMAGE))"; \
		docker run -d --name $(FI_RAG_PG_CONTAINER) \
			-e POSTGRES_PASSWORD=$(FI_RAG_PG_PASSWORD) -e POSTGRES_DB=$(FI_RAG_PG_DB) \
			-p $(FI_RAG_PG_PORT):5432 $(FI_RAG_PG_IMAGE) >/dev/null; \
	fi
	@echo "  ↳ waiting for postgres"; \
	for i in $$(seq 1 30); do \
		if docker exec $(FI_RAG_PG_CONTAINER) pg_isready -U postgres -d $(FI_RAG_PG_DB) >/dev/null 2>&1; then break; fi; \
		if [ "$$i" = "30" ]; then echo "  ✗ postgres not ready after 30s" >&2; exit 1; fi; \
		sleep 1; \
	done
	@docker exec $(FI_RAG_PG_CONTAINER) psql -U postgres -d $(FI_RAG_PG_DB) \
		-c 'CREATE EXTENSION IF NOT EXISTS vector;' >/dev/null
	cd apps/packages/fi-core && \
		FI_RAG_PGVECTOR_TEST_DSN="$(FI_RAG_PGVECTOR_TEST_DSN)" \
		$(PY) -m pytest tests/test_rag_pgvector_smoke.py -v -m integration

test-rag-smoke-down: ## Stop & remove the throwaway pgvector smoke container
	@docker rm -f $(FI_RAG_PG_CONTAINER) >/dev/null 2>&1 || true
	@echo "🧹 removed $(FI_RAG_PG_CONTAINER)"

# ============================================================================
# Turborepo
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
# Housekeeping
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

print-%: ## Print any variable (usage: make print-PY)
	@echo "$* = $($*)"
