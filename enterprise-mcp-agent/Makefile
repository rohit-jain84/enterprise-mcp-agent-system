.PHONY: dev build test eval lint clean setup db-migrate mcp-test

dev:
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build

build:
	docker compose -f docker/docker-compose.yml build

test:
	cd backend && python -m pytest tests/ -v --tb=short

eval:
	cd backend && python -m evals.run_evals

lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && npx eslint .

clean:
	docker compose -f docker/docker-compose.yml down -v

setup:
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

db-migrate:
	cd backend && alembic upgrade head

mcp-test:
	@echo "Testing GitHub MCP server..."
	curl -sf http://localhost:8001/health && echo " OK" || echo " FAILED"
	@echo "Testing Project Management MCP server..."
	curl -sf http://localhost:8002/health && echo " OK" || echo " FAILED"
	@echo "Testing Calendar MCP server..."
	curl -sf http://localhost:8003/health && echo " OK" || echo " FAILED"
