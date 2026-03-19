# Milestone 7: Unified Chat View & Status Management

**Status:** `DONE`
**Goal:** Merge all chats into one conversation view. Status upload + management.

## Commits

| # | Description | Commit Message | Status |
|---|-------------|---------------|--------|
| 7.1 | API: unified chat stream with inline event markers | `feat: add unified chat stream api` | `DONE` |
| 7.2 | Frontend: Chat View toggle with continuous conversation | `feat: add chat view with timeline toggle` | `DONE` |
| 7.3 | Frontend: inline event markers (calls, statuses) in chat | `feat: add inline event markers in chat view` | `DONE` |
| 7.4 | Frontend: status gallery with platform badges and playback | `feat: add status gallery view` | `DONE` |
| 7.5 | Frontend: editable status timestamps with auto-reorder | `feat: add editable status timestamps` | `DONE` |
| 7.6 | Integration tests: chat stream and status management | `test: add chat view and status tests` | `DONE` |

## Test Results

```
85 passed in 6.20s
```

8 new tests: chat stream empty, messages only, events only, mixed chronological,
transcript summary, source tracking, 404 handling, timestamp reorder verification.

## Acceptance Criteria

- [x] Chat View merges all chat groups into one conversation
- [x] Non-chat items appear as inline markers
- [x] Source indicators show which screenshot group each section came from
- [x] Status gallery shows all statuses with platform filtering
- [x] Editing status timestamps re-sorts the gallery
- [x] Timeline ↔ Chat view toggle works seamlessly
