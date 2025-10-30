.PHONY: help install run-eval run-prod validate report all clean health

# Production environment variables
EVAL_MODE ?= prod
EVAL_PROVIDER ?= ollama
EVAL_MODEL ?= qwen2:7b
EVAL_SEED ?= fi-obs-001
EVAL_CACHE_POLICY ?= measure-both
EVAL_QPS ?= 1
EVAL_WARMUP ?= 8
FI_API_BASE ?= http://localhost:7001

help:
	@echo "Free Intelligence — Evaluation Makefile (FI-OBS-RES-001)"
	@echo ""
	@echo "Commands:"
	@echo "  make install     - Install Python dependencies (jsonschema, numpy, requests)"
	@echo "  make run-prod    - Run PRODUCTION evaluation (NO MOCKS)"
	@echo "  make validate    - Validate results against metrics.schema.json"
	@echo "  make report      - Generate QA_REPORT.md from results + manifest"
	@echo "  make all         - Run full workflow: run-prod -> validate -> report"
	@echo "  make health      - Check API health before running"
	@echo "  make clean       - Remove all result files"
	@echo ""
	@echo "Production Environment:"
	@echo "  EVAL_MODE=${EVAL_MODE}"
	@echo "  EVAL_PROVIDER=${EVAL_PROVIDER}"
	@echo "  EVAL_MODEL=${EVAL_MODEL}"
	@echo "  EVAL_SEED=${EVAL_SEED}"
	@echo "  EVAL_CACHE_POLICY=${EVAL_CACHE_POLICY}"
	@echo "  EVAL_QPS=${EVAL_QPS}"
	@echo "  EVAL_WARMUP=${EVAL_WARMUP}"
	@echo "  FI_API_BASE=${FI_API_BASE}"
	@echo ""
	@echo "Example (Production):"
	@echo "  make all EVAL_PROVIDER=ollama EVAL_MODEL=qwen2:7b EVAL_CACHE_POLICY=measure-both"

install:
	@echo "📦 Installing dependencies..."
	pip install jsonschema numpy requests

health:
	@echo "🏥 Checking API health..."
	@curl -sf ${FI_API_BASE}/health > /dev/null && echo "✅ API healthy" || (echo "❌ API not responding"; exit 1)

run-prod: health
	@echo "🚀 Running PRODUCTION evaluation (NO MOCKS)"
	@echo "   Provider: ${EVAL_PROVIDER}"
	@echo "   Model: ${EVAL_MODEL}"
	@echo "   Cache: ${EVAL_CACHE_POLICY}"
	@echo "   Seed: ${EVAL_SEED}"
	@echo ""
	EVAL_MODE=${EVAL_MODE} \
	EVAL_PROVIDER=${EVAL_PROVIDER} \
	EVAL_MODEL=${EVAL_MODEL} \
	EVAL_SEED=${EVAL_SEED} \
	EVAL_CACHE_POLICY=${EVAL_CACHE_POLICY} \
	EVAL_QPS=${EVAL_QPS} \
	EVAL_WARMUP=${EVAL_WARMUP} \
	FI_API_BASE=${FI_API_BASE} \
	python3 run_eval.py --provider ${EVAL_PROVIDER} --model ${EVAL_MODEL} --seed ${EVAL_SEED} --cache-policy ${EVAL_CACHE_POLICY} --qps ${EVAL_QPS} --warmup ${EVAL_WARMUP}

# Legacy dry-run (deprecated)
run-eval:
	@echo "⚠️  DEPRECATED: Use 'make run-prod' instead"
	@echo "   This target is kept for backward compatibility only"
	@echo ""
	python3 run_eval.py --seed ${EVAL_SEED} --prompts prompts.csv

validate:
	@echo "✅ Validating results against schema..."
	@latest=$$(ls -t results/run_*.json 2>/dev/null | head -1); \
	if [ -z "$$latest" ]; then \
		echo "❌ No results found. Run 'make run-eval' first."; \
		exit 1; \
	else \
		echo "Validating: $$latest"; \
		python3 -c "import json, jsonschema; \
			schema = json.load(open('metrics.schema.json')); \
			data = json.load(open('$$latest')); \
			jsonschema.validate(data, schema); \
			print('✅ Schema validation PASSED')"; \
	fi

report:
	@echo "📊 Generating QA Report..."
	python3 generate_qa_report.py
	@echo ""
	@echo "Report saved: eval/report/QA_REPORT.md"
	@echo ""
	@tail -20 report/QA_REPORT.md

all: run-prod validate report
	@echo ""
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "✅ Evaluation workflow complete"
	@echo "════════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Artifacts:"
	@echo "  - Results:  eval/results/run_*.json"
	@echo "  - Manifest: eval/results/manifest.json"
	@echo "  - Report:   eval/report/QA_REPORT.md"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Review report: cat eval/report/QA_REPORT.md"
	@echo "  2. Verify hashes: sha256sum eval/prompts.csv eval/results/manifest.json"
	@echo "  3. Attach to Trello: FI-OBS-RES-001"
	@echo ""

clean:
	rm -rf results/run_*.json results/manifest.json report/QA_REPORT.md
	@echo "✅ Cleaned: results/ and report/"
