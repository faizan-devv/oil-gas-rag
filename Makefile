.DEFAULT_GOAL := help
.PHONY: help install corpus index ask eval-rag extract eval-prompts evals test serve docker-build docker-run docker-run-host clean

IMAGE ?= field-qa
PORT ?= 8000
Q ?= What does the manual say about replacing the mud pump seal?

help: ## List the available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "} {printf "  %-16s %s\n", $$1, $$2}'

install: ## Create the virtualenv and install dependencies
	uv sync

corpus: ## Regenerate the synthetic corpus and gold records (calls the LLM)
	uv run python scripts/generate_corpus.py

index: ## Rebuild the vector index from data/raw
	uv run python -c "from app.rag import store; print(store.build_index(force=True))"

ask: ## Ask one question: make ask Q="How often is the BOP stack pressure tested?"
	uv run python -m app.rag.pipeline "$(Q)"

eval-rag: ## Task 1: run the RAG test questions -> outputs/rag_eval.md
	uv run python scripts/eval_rag.py

extract: ## Task 2: extract maintenance logs -> outputs/records.csv, maintenance.db, quarantine.jsonl
	uv run python -m app.extraction.run

eval-prompts: ## Task 3: compare the three prompt strategies -> outputs/prompt_eval.md
	uv run python -m app.prompts.run_eval

evals: eval-rag extract eval-prompts ## Run all three evaluations

test: ## Task 4: run the API tests (offline, no model server needed)
	uv run pytest

serve: ## Task 4: run the API locally on port 8000 (override with PORT=)
	uv run uvicorn app.api.main:app --port $(PORT)

docker-build: ## Build the API image
	docker build -t $(IMAGE) .

docker-run: ## Run the API image on the default bridge network
	docker run --rm --env-file .env -p $(PORT):8000 $(IMAGE)

docker-run-host: ## Run the API image on the host network (model servers behind a host VPN)
	docker run --rm --env-file .env --network host $(IMAGE)

clean: ## Remove the vector index and Python caches
	rm -rf data/index .pytest_cache
	find . -name __pycache__ -not -path './.venv/*' -type d -prune -exec rm -rf {} +
