.PHONY: help up down restart logs seed migrate test lint format

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ---- Docker ----

up: ## Start all services
	docker compose up -d
	@echo "\n✅ Services started:"
	@echo "  Backend:  http://localhost:8000"
	@echo "  AI Core:  http://localhost:8001"
	@echo "  Frontend: http://localhost:3000"
	@echo "  MinIO:    http://localhost:9001"
	@echo "  Docs:     http://localhost:8000/api/v1/openapi.json"

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

logs: ## Tail logs for all services
	docker compose logs -f --tail=50

logs-backend: ## Tail backend logs
	docker compose logs -f --tail=50 backend

logs-ai: ## Tail AI Core logs
	docker compose logs -f --tail=50 ai-core

# ---- Database ----

migrate: ## Run database migrations
	cd backend && alembic upgrade head

migrate-create: ## Create a new migration (use: make migrate-create msg="description")
	cd backend && alembic revision --autogenerate -m "$(msg)"

seed: ## Seed database with demo data
	cd backend && python -m scripts.seed

db-shell: ## Open psql shell
	docker compose exec postgres psql -U postgres -d bankruptcy_ai

db-reset: ## Reset database (drop + recreate + migrate + seed)
	docker compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS bankruptcy_ai"
	docker compose exec postgres psql -U postgres -c "CREATE DATABASE bankruptcy_ai"
	$(MAKE) migrate
	$(MAKE) seed

# ---- Backend ----

backend-dev: ## Run backend in dev mode (without docker)
	cd backend && uvicorn app.main:app --reload --port 8000

test: ## Run backend tests
	cd backend && python -m pytest tests/ -v

test-cov: ## Run tests with coverage
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing

lint: ## Lint backend code
	cd backend && ruff check .

format: ## Format backend code
	cd backend && ruff format .

# ---- Frontend ----

frontend-dev: ## Run frontend in dev mode (without docker)
	cd frontend && npm run dev

frontend-build: ## Build frontend
	cd frontend && npm run build

frontend-lint: ## Lint frontend
	cd frontend && npm run lint

# ---- AI Core ----

ai-dev: ## Run AI Core in dev mode (without docker)
	cd ai-core && uvicorn main:app --reload --port 8001

# ---- Utilities ----

install: ## Install all dependencies locally
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

install-dev: ## Install backend dev/test dependencies
	cd backend && pip install -r requirements-dev.txt

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null; true
	find . -name "*.pyc" -delete 2>/dev/null; true

health: ## Check health of all services
	@echo "Backend:"
	@curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "  ❌ not running"
	@echo "\nAI Core:"
	@curl -s http://localhost:8001/health | python3 -m json.tool 2>/dev/null || echo "  ❌ not running"
	@echo "\nFrontend:"
	@curl -s -o /dev/null -w "  Status: %{http_code}\n" http://localhost:3000 2>/dev/null || echo "  ❌ not running"

worker: ## Run AI task worker
	cd backend && python -m app.services.worker

lead-collect: ## Run gov lead collectors once
	cd backend && python3 -m workers.lead_collectors --once

lead-outreach: ## Run outreach worker once
	cd backend && python3 -m workers.outreach --once

lead-collect-daemon: ## Run gov lead collectors continuously
	cd backend && python3 -m workers.lead_collectors

lead-outreach-daemon: ## Run outreach worker continuously
	cd backend && python3 -m workers.outreach

telegram: ## Start with Telegram bot
	docker compose --profile telegram up -d

new-case: ## Quick: create test client + case via API
	@echo "Creating test client and case..."
	@curl -s -X POST http://localhost:8000/api/v1/auth/seed-admin | python3 -m json.tool 2>/dev/null || true
	@TOKEN=$$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
		-H 'Content-Type: application/json' \
		-d '{"email":"admin@bankruptcy.ai","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])" 2>/dev/null) && \
	CLIENT_ID=$$(curl -s -X POST http://localhost:8000/api/v1/clients/ \
		-H "Content-Type: application/json" \
		-H "Authorization: Bearer $$TOKEN" \
		-d '{"first_name":"Тест","last_name":"Тестов","phone":"+79999999999"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])" 2>/dev/null) && \
	curl -s -X POST http://localhost:8000/api/v1/cases/ \
		-H "Content-Type: application/json" \
		-H "Authorization: Bearer $$TOKEN" \
		-d "{\"client_id\":\"$$CLIENT_ID\",\"total_debt\":850000}" | python3 -m json.tool
