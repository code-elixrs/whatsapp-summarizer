# Milestone 8: Search & Polish

**Status:** `PENDING`
**Goal:** Cross-space search, full-text search, UX polish, production hardening.

## Commits

| # | Description | Commit Message | Status |
|---|-------------|---------------|--------|
| 8.1 | PostgreSQL full-text search across all content | `feat: add full-text search with pg tsvector` | `PENDING` |
| 8.2 | API: global search endpoint with grouped results | `feat: add global search api` | `PENDING` |
| 8.3 | Frontend: global search with navigation to results | `feat: add global search ui` | `PENDING` |
| 8.4 | Frontend: within-space search with type filtering | `feat: add in-space search with filters` | `PENDING` |
| 8.5 | Frontend: loading, empty, error states, delete confirmations | `feat: add ux polish and state handling` | `PENDING` |
| 8.6 | Docker: production compose with volumes, restarts, health checks | `feat: add production docker-compose config` | `PENDING` |
| 8.7 | Documentation: README with setup and architecture | `docs: add readme with setup instructions` | `PENDING` |
| 8.8 | Final integration test suite: full user journey | `test: add end-to-end user journey tests` | `PENDING` |

## Acceptance Criteria

- [ ] Global search returns results across all spaces
- [ ] Full-text search covers transcripts, OCR text, chat messages
- [ ] Search results link to items within their spaces
- [ ] Within-space search filters by content type
- [ ] All UI states handled (loading, empty, error, confirmation)
- [ ] Production Docker Compose with proper resource management
- [ ] README enables setup from scratch
- [ ] E2E test covers: create space → upload → process → search → view
