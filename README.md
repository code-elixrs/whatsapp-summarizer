# LifeLog

Personal, open-source web app to organize call recordings, chat screenshots, and social media statuses into a unified, searchable timeline per person.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose (v2+)
- That's it. Everything runs inside containers.

## Quick Start

```bash
# 1. Copy environment config
cp .env.example .env

# 2. Start all services
make up

# 3. Run database migrations
make migrate

# 4. Open the app
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs (Swagger UI)
# Health check: http://localhost:8000/api/health
```

## Available Commands

All commands run inside Docker — nothing is installed on your host machine.

| Command | Description |
|---------|-------------|
| `make up` | Build and start all services |
| `make down` | Stop all services |
| `make clean` | Stop services and delete all data (volumes) |
| `make rebuild` | Full rebuild from scratch (no cache) |
| `make logs` | Follow logs from all services |
| `make logs-service s=api` | Follow logs for a specific service (`api`, `celery`, `db`, `redis`, `frontend`) |
| `make test` | Run all tests (backend + frontend) |
| `make test-backend` | Run backend tests (pytest) |
| `make test-frontend` | Run frontend tests (vitest) |
| `make migrate` | Apply database migrations |
| `make makemigrations msg="description"` | Generate a new migration |
| `make shell` | Open bash inside the API container |
| `make lint` | Run Python linter (ruff) |
| `make status` | Show running containers and their status |

## Services

| Service | Port | Description |
|---------|------|-------------|
| `frontend` | 3000 | React (Vite) dev server |
| `api` | 8000 | FastAPI backend |
| `celery` | — | Background task worker |
| `db` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 (task broker) |

## Project Structure

```
├── docker-compose.yml       # Service orchestration
├── Makefile                 # Developer commands
├── .env.example             # Environment template
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py          # FastAPI app
│   │   ├── core/            # Config, database
│   │   ├── api/             # Route handlers
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── middleware/      # Error handling, CORS
│   │   └── tasks/           # Celery tasks
│   ├── alembic/             # DB migrations
│   └── tests/               # Backend tests
├── frontend/
│   ├── Dockerfile
│   └── src/
│       ├── components/      # React components
│       ├── pages/           # Page components
│       ├── styles/          # CSS & design tokens
│       └── lib/             # API client
└── docs/
    ├── PRD.md               # Product requirements
    └── milestones/          # Implementation tracker
```

## Updating After Code Changes

```bash
# Pull latest code
git pull

# Rebuild and restart (picks up new dependencies, Dockerfile changes, etc.)
make rebuild

# Apply any new migrations
make migrate

# Verify everything is healthy
make status
make test
```

If only source code changed (no new dependencies), a faster restart:
```bash
docker compose up -d --build
make migrate
```

## Troubleshooting

**Services won't start:**
```bash
make status          # Check which services are running
make logs-service s=api   # Check logs for the failing service
```

**Database issues:**
```bash
make clean           # Reset everything (deletes data)
make up
make migrate
```

**Stale containers after code changes:**
```bash
make rebuild         # Full rebuild, no cache
```

**Port conflicts:**
If ports 3000, 8000, 5432, or 6379 are in use, stop the conflicting services or edit `docker-compose.yml` to change the host port mappings.
