.PHONY: help run-eval report clean install

help:
	@echo "Free Intelligence — Evaluation Makefile"
	@echo ""
	@echo "Commands:"
	@echo "  make install     - Install Python dependencies (jsonschema, numpy)"
	@echo "  make run-eval    - Run evaluation against prompts.csv"
	@echo "  make report      - Display latest results"
	@echo "  make clean       - Remove all result files"

install:
	pip install jsonschema numpy

run-eval:
	python3 run_eval.py

report:
	@latest=$$(ls -t results/*.json 2>/dev/null | head -1); \
	if [ -z "$$latest" ]; then \
		echo "❌ No results found. Run 'make run-eval' first."; \
	else \
		echo "📊 Latest Results: $$latest"; \
		cat "$$latest" | python3 -m json.tool | head -50; \
	fi

clean:
	rm -rf results/*.json
	@echo "✅ Cleaned results/"
