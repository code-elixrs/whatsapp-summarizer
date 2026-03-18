# Milestone 3: File Upload & Storage

**Status:** `PENDING`
**Goal:** Upload files into a space, store on filesystem, show in timeline.

## Commits

| # | Description | Commit Message | Status |
|---|-------------|---------------|--------|
| 3.1 | API: multipart upload endpoint with file type detection, local storage | `feat: add file upload endpoint with local storage` | `PENDING` |
| 3.2 | MediaItem model: type, user timestamp, file metadata, validation | `feat: add media item model and validation` | `PENDING` |
| 3.3 | Frontend: upload zone with drag-drop, type selector, datetime picker | `feat: add upload ui with drag-drop and metadata` | `PENDING` |
| 3.4 | Frontend: upload progress via polling | `feat: add upload progress tracking` | `PENDING` |
| 3.5 | API: paginated, filtered, sorted items listing | `feat: add items listing api with filters` | `PENDING` |
| 3.6 | Frontend: timeline view rendering items by type with expand/collapse | `feat: add timeline view with expandable items` | `PENDING` |
| 3.7 | API: edit timestamp/type/notes, delete items | `feat: add item edit and delete endpoints` | `PENDING` |
| 3.8 | API: serve stored files (images, audio, video) | `feat: add file serving endpoint` | `PENDING` |
| 3.9 | Integration tests: upload → list → edit → delete flow | `test: add upload and items lifecycle tests` | `PENDING` |

## Acceptance Criteria

- [ ] User can upload files with drag & drop
- [ ] Each file gets a content type and datetime assignment
- [ ] Uploaded files appear in timeline sorted by timestamp
- [ ] Timeline items expand/collapse to show previews
- [ ] Images display, audio plays, video plays inline
- [ ] Timestamps are editable with auto-reorder
- [ ] Items can be deleted
- [ ] Full lifecycle covered by integration tests
