# Free Intelligence - Makefile
# Convenience commands for development and deployment

.PHONY: help setup install install-dev test run run-gateway run-both clean docker-build docker-run docker-stop lint format fmt check-deps init-corpus

# Default target
.DEFAULT_GOAL := help

# ============================================================================
# Help
# ============================================================================

help: ## Show this help message
	@echo "Free Intelligence - Available Commands"
	@echo "======================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Installation
# ============================================================================

setup: install init-corpus ## Full monorepo setup (install + init)
	@echo "✅ Free Intelligence monorepo initialized"
	@echo "   - Backend: Python packages installed"
	@echo "   - Corpus: storage/corpus.h5 ready"
	@echo "   - Frontend: apps/aurity (submodule)"

install: ## Install all dependencies
	pip install -e .
	@echo "✅ Dependencies installed"

install-dev: ## Install dependencies + dev tools
	pip install -e ".[dev]"
	@echo "✅ Dev dependencies installed"

check-deps: ## Check if all dependencies are installed
	@python3 -c "import h5py; import structlog; import fastapi; import anthropic; import ollama" && echo "✅ All dependencies OK" || echo "❌ Missing dependencies - run 'make install'"

# ============================================================================
# Initialization
# ============================================================================

init-corpus: ## Initialize HDF5 corpus (if not exists)
	@if [ ! -f storage/corpus.h5 ]; then \
		echo "📂 Initializing corpus..."; \
		mkdir -p storage; \
		python3 backend/corpus_schema.py init bernard.uriza@example.com; \
		echo "✅ Corpus initialized"; \
	else \
		echo "ℹ️  Corpus already exists at storage/corpus.h5"; \
	fi

init: install init-corpus ## Full initialization (install + init corpus)
	@echo "✅ Free Intelligence initialized"

# ============================================================================
# Running Services
# ============================================================================

run: init-corpus ## Run FI Consult Service (port 7001)
	@echo "🚀 Starting FI Consult Service on http://localhost:7001"
	@echo "   Health check: http://localhost:7001/health"
	@echo "   Press Ctrl+C to stop"
	@echo ""
	PYTHONPATH=. python3 -m uvicorn backend.fi_consult_service:app --host 0.0.0.0 --port 7001 --reload

run-gateway: init-corpus ## Run AURITY Gateway (port 7002)
	@echo "🚀 Starting AURITY Gateway on http://localhost:7002"
	@echo "   Health check: http://localhost:7002/health"
	@echo "   Press Ctrl+C to stop"
	@echo ""
	PYTHONPATH=. python3 -m uvicorn backend.aurity_gateway:app --host 0.0.0.0 --port 7002 --reload

run-both: init-corpus ## Run both services (requires tmux or separate terminals)
	@echo "🚀 Starting both services..."
	@echo "   FI Consult:    http://localhost:7001"
	@echo "   AURITY Gateway: http://localhost:7002"
	@echo ""
	@echo "Run these in separate terminals:"
	@echo "  Terminal 1: make run"
	@echo "  Terminal 2: make run-gateway"

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests
	@echo "🧪 Running tests..."
	python3 -m pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage
	@echo "🧪 Running tests with coverage..."
	python3 -m pytest tests/ -v --cov=backend --cov-report=html --cov-report=term

test-scenario-1: ## Run QA Scenario 1 (green path)
	@echo "🧪 Running Scenario 1: Green Path"
	bash test_scenario_1.sh

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run linter (ruff)
	@echo "🔍 Linting code..."
	ruff check backend/ tests/

format: ## Format code (black)
	@echo "✨ Formatting code..."
	black backend/ tests/

fmt: format ## Alias for format

format-check: ## Check code formatting
	@echo "🔍 Checking code formatting..."
	black --check backend/ tests/

type-check: ## Run type checker (mypy)
	@echo "🔍 Type checking..."
	mypy backend/ --ignore-missing-imports

# ============================================================================
# Docker
# ============================================================================

docker-build: ## Build Docker image
	@echo "🐳 Building Docker image..."
	docker build -t free-intelligence:latest -t free-intelligence:0.3.0 .
	@echo "✅ Docker image built: free-intelligence:latest"

docker-run: ## Run Docker container (FI Consult Service)
	@echo "🐳 Running Docker container..."
	docker run -d \
		--name fi-consult \
		-p 7001:7001 \
		-v $(PWD)/storage:/app/storage \
		-v $(PWD)/logs:/app/logs \
		free-intelligence:latest
	@echo "✅ Container started: fi-consult"
	@echo "   Health: http://localhost:7001/health"

docker-run-gateway: ## Run Docker container (AURITY Gateway)
	@echo "🐳 Running AURITY Gateway container..."
	docker run -d \
		--name fi-gateway \
		-p 7002:7002 \
		-v $(PWD)/storage:/app/storage \
		-v $(PWD)/logs:/app/logs \
		free-intelligence:latest \
		python3 -m uvicorn backend.aurity_gateway:app --host 0.0.0.0 --port 7002
	@echo "✅ Container started: fi-gateway"
	@echo "   Health: http://localhost:7002/health"

docker-stop: ## Stop all Docker containers
	@echo "🛑 Stopping Docker containers..."
	-docker stop fi-consult fi-gateway
	-docker rm fi-consult fi-gateway
	@echo "✅ Containers stopped"

docker-logs: ## Show Docker logs
	docker logs -f fi-consult

docker-shell: ## Open shell in running container
	docker exec -it fi-consult /bin/bash

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Clean generated files
	@echo "🧹 Cleaning..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned"

clean-all: clean docker-stop ## Clean everything (including Docker)
	@echo "🧹 Deep cleaning..."
	rm -rf htmlcov/ .coverage
	@echo "✅ Deep clean complete"

# ============================================================================
# Utilities
# ============================================================================

health-check: ## Check service health
	@echo "🏥 Checking FI Consult Service..."
	@curl -s http://localhost:7001/health | jq . || echo "❌ Service not responding"
	@echo ""
	@echo "🏥 Checking AURITY Gateway..."
	@curl -s http://localhost:7002/health | jq . || echo "❌ Gateway not responding"

corpus-stats: ## Show corpus statistics
	@echo "📊 Corpus Statistics"
	@python3 backend/fi_event_store.py stats

audit-logs: ## Show recent audit logs
	@echo "📜 Recent Audit Logs"
	@python3 backend/audit_logs.py show

trello-status: ## Show Trello sprint status
	@echo "📋 Trello Sprint Status"
	@~/Documents/trello-cli-python/trello cards 68fc011510584fb24b9ef5a6 | head -20

# ============================================================================
# Info
# ============================================================================

info: ## Show project information
	@echo "Free Intelligence - Project Info"
	@echo "================================="
	@echo "Version:     0.3.0"
	@echo "Python:      $(shell python3 --version)"
	@echo "Directory:   $(PWD)"
	@echo "Corpus:      storage/corpus.h5 $(shell [ -f storage/corpus.h5 ] && echo '✅' || echo '❌')"
	@echo "Services:"
	@echo "  - FI Consult:    port 7001"
	@echo "  - AURITY Gateway: port 7002"
	@echo ""
	@echo "Quick Start:"
	@echo "  make init      # Initialize project"
	@echo "  make run       # Start FI Consult Service"
	@echo "  make test      # Run tests"
