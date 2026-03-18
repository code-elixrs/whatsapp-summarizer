# Milestone 6: Screenshot Stitching

**Status:** `PENDING`
**Goal:** Multiple screenshots → detect overlap → stitch into one image.

## Commits

| # | Description | Commit Message | Status |
|---|-------------|---------------|--------|
| 6.1 | Celery task: stitch_screenshots with OpenCV feature matching | `feat: add screenshot stitching task` | `PENDING` |
| 6.2 | API: auto-trigger stitching for grouped chat screenshots | `feat: wire stitching pipeline for screenshot groups` | `PENDING` |
| 6.3 | Fallback: graceful handling when stitching fails | `feat: add stitching fallback with manual review flag` | `PENDING` |
| 6.4 | Frontend: three-tab view (Chat / Stitched / Originals) | `feat: add three-tab stitch view` | `PENDING` |
| 6.5 | Frontend: drag-drop reorder originals and re-stitch | `feat: add screenshot reorder and re-stitch` | `PENDING` |
| 6.6 | Integration tests: stitching with sample screenshots | `test: add stitching pipeline tests` | `PENDING` |

## Acceptance Criteria

- [ ] Multiple screenshots stitch into one vertical image
- [ ] Overlap regions detected and merged cleanly
- [ ] Stitching failure falls back gracefully (keeps originals)
- [ ] Three-tab view: Chat bubbles / Stitched image / Originals
- [ ] Users can reorder screenshots and re-trigger stitching
- [ ] Pipeline covered by integration tests
