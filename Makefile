.PHONY: help install dev test lint migrate seed sync build clean docker-up docker-down

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

# Installation
install-backend: ## Install backend dependencies
	cd backend && uv sync --all-groups

install-frontend: ## Install frontend dependencies
	cd frontend && npm install

install: install-backend install-frontend ## Install all dependencies

# Development
dev-backend: ## Start backend development server
	cd backend && uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8003

dev-frontend: ## Start frontend development server
	cd frontend && npm run dev

dev: ## Start all services with docker-compose
	cd deploy && docker-compose up

# Testing
test-backend: ## Run backend tests
	cd backend && uv run pytest --cov=app --cov-report=term-missing

test-frontend: ## Run frontend tests
	cd frontend && npm run test

test: test-backend test-frontend ## Run all tests

# Linting
lint-backend: ## Lint backend code (ruff + black)
	cd backend && uv run ruff check app tests
	cd backend && uv run black --check app tests

lint-backend-full: ## Full backend lint (ruff + black + mypy gate + architecture check)
	cd backend && uv run ruff check app tests
	cd backend && uv run black --check app tests
	cd backend && uv run python scripts/mypy_gate.py
	cd backend && uv run python scripts/check_architecture.py

lint-frontend: ## Run frontend linting
	cd frontend && npm run lint

lint-frontend-full: ## Full frontend lint (lint + audit + build)
	cd frontend && npm run lint
	cd frontend && npm audit --registry https://registry.npmjs.org
	cd frontend && npm run build

lint: lint-backend lint-frontend ## Run all linting

lint-full: lint-backend-full lint-frontend-full ## Run all linting + gates (matches CI)

# Database
migrate: ## Run database migrations
	cd backend && uv run alembic upgrade head

migrate-create: ## Create a new migration
	cd backend && uv run alembic revision --autogenerate -m "$(msg)"

migrate-rollback: ## Rollback last migration
	cd backend && uv run alembic downgrade -1

# Data Pipeline
seed: ## Seed database with initial data
	cd backend && uv run python scripts/seed.py

sync: ## Run OpenAlex sync task
	cd backend && uv run python scripts/sync.py

sync-test: ## Test OpenAlex API connection
	cd backend && uv run python scripts/sync.py --test-connection

build-objects: ## Build domain objects from raw data
	cd backend && uv run python scripts/build_objects.py

pipeline: migrate seed ## Run full pipeline: migrate + seed
	@echo "Pipeline complete!"

# Docker
docker-up: ## Start all services with docker-compose
	cd deploy && docker-compose up -d

docker-down: ## Stop all services
	cd deploy && docker-compose down

docker-logs: ## Show docker logs
	cd deploy && docker-compose logs -f

# Cleanup
clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "node_modules" -exec rm -rf {} +
	find . -type d -name "dist" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
