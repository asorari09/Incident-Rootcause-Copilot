.PHONY: install test run-api run-web eval index-runbooks

install:
	uv sync
	cd apps/web && npm install

test:
	PYTHONPATH=apps/api/src uv run python -m unittest discover -s tests -v

run-api:
	PYTHONPATH=apps/api/src uv run uvicorn ir_copilot.main:app --host 127.0.0.1 --port 8000 --reload

run-web:
	cd apps/web && npm run dev

eval:
	uv run python evals/run_evals.py

index-runbooks:
	PYTHONPATH=apps/api/src uv run python -c "from ir_copilot.rag.indexer import main; main()"
