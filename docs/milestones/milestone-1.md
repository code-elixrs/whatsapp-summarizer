# Milestone 1: Project Foundation & Infrastructure

**Status:** `IN PROGRESS`
**Goal:** Docker Compose setup, database, backend skeleton, frontend skeleton — app boots and shows empty UI.

## Commits

| # | Description | Commit Message | Status |
|---|-------------|---------------|--------|
| 1.1 | Docker Compose with PostgreSQL, Redis, FastAPI, React (Vite), Celery worker | `feat: add docker-compose with core services` | `PENDING` |
| 1.2 | FastAPI project: config, health endpoint, DB connection, Alembic migrations | `feat: setup fastapi with db and alembic migrations` | `PENDING` |
| 1.3 | SQLAlchemy models: Space, MediaItem, Transcript, ChatMessage | `feat: add core database models` | `PENDING` |
| 1.4 | React scaffold: router, layout shell, dark theme | `feat: scaffold react app with routing and dark theme` | `PENDING` |
| 1.5 | API error handling, CORS, logging, test configs (pytest + vitest) | `feat: add error handling, cors, and test infrastructure` | `PENDING` |

## Acceptance Criteria

- [ ] `docker compose up` boots all services without errors
- [ ] `GET /api/health` returns `200 OK` with DB connection status
- [ ] Alembic migration creates all tables in PostgreSQL
- [ ] Frontend loads at `http://localhost:3000` with dark theme shell
- [ ] `make test` runs backend (pytest) and frontend (vitest) test suites
- [ ] Celery worker connects to Redis and is ready to receive tasks
- [ ] All services restart gracefully on failure
