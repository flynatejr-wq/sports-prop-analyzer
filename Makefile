.PHONY: help up down build logs backend frontend install migrate migration format test-backend type-check restart shell-backend shell-db

help:
	@echo "PropEdge AI — Make targets"
	@echo ""
	@echo "Docker (production-like):"
	@echo "  make up             Start all services (NGINX + backend + frontend + DB)"
	@echo "  make down           Stop and remove containers"
	@echo "  make build          Rebuild all images"
	@echo "  make restart        Rebuild and restart"
	@echo "  make logs           Tail logs from all services"
	@echo ""
	@echo "Local development (no Docker):"
	@echo "  make backend        Run backend with hot-reload"
	@echo "  make frontend       Run frontend dev server"
	@echo "  make install        Install all dependencies"
	@echo ""
	@echo "Database:"
	@echo "  make migrate        Run pending Alembic migrations"
	@echo "  make migration name=add_players   Generate a new migration"
	@echo "  make shell-db       Open psql shell"
	@echo ""
	@echo "Code quality:"
	@echo "  make format         Format Python (ruff) + TypeScript (prettier)"
	@echo "  make type-check     TypeScript type-check"
	@echo "  make test-backend   Run pytest"
	@echo ""

up:
	docker compose up -d
	@echo ""
	@echo "PropEdge AI running:"
	@echo "  App:      http://localhost"
	@echo "  API:      http://localhost/api/v1/props/top"
	@echo "  Docs:     http://localhost/docs"

down:
	docker compose down

build:
	docker compose build --parallel

restart: build
	docker compose up -d --remove-orphans

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

# ── Local dev (requires venv activated) ──────────────────────────────────────
backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

install:
	cd backend && pip install -r requirements.txt && playwright install chromium
	cd frontend && npm install --legacy-peer-deps

# ── Database ──────────────────────────────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head

migration:
	docker compose exec backend alembic revision --autogenerate -m "$(name)"

shell-db:
	docker compose exec postgres psql -U postgres -d sportsprops

shell-backend:
	docker compose exec backend bash

# ── Code quality ──────────────────────────────────────────────────────────────
format:
	cd backend && pip install ruff --quiet && ruff format app/ && ruff check app/ --fix
	cd frontend && npx prettier --write "src/**/*.{ts,tsx}"

test-backend:
	cd backend && python -m pytest tests/ -v

type-check:
	cd frontend && npm run type-check
