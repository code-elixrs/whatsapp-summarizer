.PHONY: up down logs test test-backend test-frontend migrate makemigrations shell lint rebuild

# Start all services (builds if needed)
up:
	docker compose up -d --build

# Stop all services
down:
	docker compose down

# Stop and remove volumes (clean slate)
clean:
	docker compose down -v

# Rebuild all containers from scratch
rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up -d

# Follow logs (all services)
logs:
	docker compose logs -f

# Follow logs for a specific service: make logs-service s=api
logs-service:
	docker compose logs -f $(s)

# Run all tests
test: test-backend test-frontend

# Run backend tests
test-backend:
	docker compose exec api python -m pytest -v

# Run frontend tests
test-frontend:
	docker compose exec frontend npm test

# Run database migrations
migrate:
	docker compose exec api python -m alembic upgrade head

# Create new migration: make makemigrations msg="add users table"
makemigrations:
	docker compose exec api python -m alembic revision --autogenerate -m "$(msg)"

# Open a shell inside the API container
shell:
	docker compose exec api bash

# Run linter
lint:
	docker compose exec api python -m ruff check .

# Check service health
status:
	docker compose ps
