# Milestone 3: File Upload & Storage

**Status:** `DONE`
**Goal:** Upload files into a space, store on filesystem, show in timeline.

## Commits

| # | Description | Commit Message | Status |
|---|-------------|---------------|--------|
| 3.1 | API: multipart upload endpoint with file type detection, local storage | `feat: add file upload endpoint with local storage` | `DONE` |
| 3.2 | MediaItem model: type, user timestamp, file metadata, validation | `feat: add media item model and validation` | `DONE` |
| 3.3 | Frontend: upload zone with drag-drop, type selector, datetime picker | `feat: add upload ui with drag-drop and metadata` | `DONE` |
| 3.4 | Frontend: upload progress via XHR tracking | `feat: add upload progress tracking` | `DONE` |
| 3.5 | API: paginated, filtered, sorted items listing | `feat: add items listing api with filters` | `DONE` |
| 3.6 | Frontend: timeline view rendering items by type with expand/collapse | `feat: add timeline view with expandable items` | `DONE` |
| 3.7 | API: edit timestamp/type/notes, delete items | `feat: add item edit and delete endpoints` | `DONE` |
| 3.8 | API: serve stored files (images, audio, video) | `feat: add file serving endpoint` | `DONE` |
| 3.9 | Integration tests: upload → list → edit → delete flow | `test: add upload and items lifecycle tests` | `DONE` |

## Acceptance Criteria

- [x] User can upload files with drag & drop
- [x] Each file gets a content type and datetime assignment
- [x] Uploaded files appear in timeline sorted by timestamp
- [x] Timeline items expand/collapse to show previews
- [x] Images display, audio plays, video plays inline
- [x] Timestamps are editable with auto-reorder
- [x] Items can be deleted
- [x] Full lifecycle covered by integration tests

## Test Results
- Backend: 31 tests passing (5 health+models, 14 spaces CRUD, 12 items/upload)
- Frontend: 2 tests passing (smoke tests)
