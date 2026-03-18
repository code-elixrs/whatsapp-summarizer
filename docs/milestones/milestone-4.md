# Milestone 4: Call Recording Transcription

**Status:** `PENDING`
**Goal:** Upload audio → async transcription → Hinglish transcript with timestamps.

## Commits

| # | Description | Commit Message | Status |
|---|-------------|---------------|--------|
| 4.1 | Celery task: transcribe_audio with faster-whisper, GPU/CPU fallback | `feat: add audio transcription celery task` | `PENDING` |
| 4.2 | Docker: faster-whisper with optional CUDA support | `feat: add gpu-optional transcription container` | `PENDING` |
| 4.3 | API: trigger transcription on audio upload, store transcript segments | `feat: wire transcription pipeline on upload` | `PENDING` |
| 4.4 | WebSocket endpoint for real-time task status updates | `feat: add websocket for processing status` | `PENDING` |
| 4.5 | Frontend: audio player with waveform and synced transcript | `feat: add audio player with synced transcript` | `PENDING` |
| 4.6 | Frontend: transcript search and click-to-seek | `feat: add transcript search and seek` | `PENDING` |
| 4.7 | Frontend: call detail expanded view with full transcript | `feat: add call detail expanded view` | `PENDING` |
| 4.8 | Integration tests: transcription pipeline e2e | `test: add transcription pipeline tests` | `PENDING` |

## Acceptance Criteria

- [ ] Audio upload triggers async transcription
- [ ] Transcription works on GPU and CPU
- [ ] Transcript has timestamped segments in Hinglish
- [ ] Audio player syncs with transcript (click to seek)
- [ ] Transcript is searchable with highlights
- [ ] Real-time status updates during processing
- [ ] Full pipeline covered by integration tests
