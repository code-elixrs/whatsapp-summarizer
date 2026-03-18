# Milestone 5: Screenshot OCR & Chat Reconstruction

**Status:** `PENDING`
**Goal:** Upload WhatsApp screenshots → OCR → structured chat messages.

## Commits

| # | Description | Commit Message | Status |
|---|-------------|---------------|--------|
| 5.1 | Celery task: ocr_screenshot with PaddleOCR, GPU/CPU fallback | `feat: add screenshot ocr celery task` | `PENDING` |
| 5.2 | Docker: PaddleOCR with optional CUDA support | `feat: add gpu-optional ocr container` | `PENDING` |
| 5.3 | WhatsApp chat parser: regex extraction of sender, message, time | `feat: add whatsapp chat format parser` | `PENDING` |
| 5.4 | API: trigger OCR on image upload, store chat messages | `feat: wire ocr pipeline on screenshot upload` | `PENDING` |
| 5.5 | Frontend: chat bubble reconstruction view | `feat: add chat bubble reconstruction view` | `PENDING` |
| 5.6 | Frontend: editable chat messages for OCR correction | `feat: add inline chat message editing` | `PENDING` |
| 5.7 | Frontend: original screenshot viewer tab | `feat: add original screenshot viewer` | `PENDING` |
| 5.8 | Integration tests: OCR + parsing pipeline | `test: add ocr and chat parsing tests` | `PENDING` |

## Acceptance Criteria

- [ ] Screenshot upload triggers async OCR
- [ ] OCR works on GPU and CPU
- [ ] WhatsApp chat format is parsed into structured messages
- [ ] Messages display as chat bubbles with sender and time
- [ ] Users can edit messages to correct OCR errors
- [ ] Original screenshots viewable alongside reconstruction
- [ ] Pipeline covered by integration tests
