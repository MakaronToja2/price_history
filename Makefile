DC := docker compose
BACKEND := $(DC) exec backend

.PHONY: help up down build rebuild logs ps shell dbshell migrate makemigrations \
        test test-cov lint format typecheck check clean nuke

help:
	@echo "Available targets:"
	@echo "  up               Start the full stack (detached)"
	@echo "  down             Stop the stack"
	@echo "  build            Build images"
	@echo "  rebuild          Build images with no cache"
	@echo "  logs             Tail logs from all services"
	@echo "  ps               Show running services"
	@echo "  shell            Django shell (shell_plus if available)"
	@echo "  dbshell          PostgreSQL client (main DB)"
	@echo "  migrate          Run Django migrations"
	@echo "  makemigrations   Generate new migrations"
	@echo "  test             Run pytest"
	@echo "  test-cov         Run pytest with coverage report"
	@echo "  lint             ruff check"
	@echo "  format           ruff format (writes changes)"
	@echo "  typecheck        mypy"
	@echo "  check            lint + typecheck + test"
	@echo "  clean            Stop stack and remove volumes"

up:
	$(DC) up -d

down:
	$(DC) down

build:
	$(DC) build

rebuild:
	$(DC) build --no-cache

logs:
	$(DC) logs -f

ps:
	$(DC) ps

shell:
	$(BACKEND) uv run python manage.py shell_plus 2>/dev/null || $(BACKEND) uv run python manage.py shell

dbshell:
	$(BACKEND) uv run python manage.py dbshell

migrate:
	$(BACKEND) uv run python manage.py migrate
	$(BACKEND) uv run python manage.py migrate --database=timeseries

makemigrations:
	$(BACKEND) uv run python manage.py makemigrations

test:
	$(BACKEND) uv run pytest

test-cov:
	$(BACKEND) uv run pytest --cov --cov-report=term-missing

lint:
	$(BACKEND) uv run ruff check .

format:
	$(BACKEND) uv run ruff format .
	$(BACKEND) uv run ruff check --fix .

typecheck:
	$(BACKEND) uv run mypy .

check: lint typecheck test

clean:
	$(DC) down -v
