# LifeLog — Product Requirements Document

## Overview

LifeLog is a personal, open-source web application for organizing and reviewing communication artifacts — call recordings, chat screenshots, social media statuses — into a unified, searchable timeline per person.

## Problem Statement

Communication happens across multiple platforms (WhatsApp, Snapchat, Instagram, phone calls). Reviewing past interactions requires opening multiple apps, scrolling through scattered media, and mentally reconstructing timelines. Screenshots saved to Google Drive lose metadata. Call recordings sit unlistened in folders.

LifeLog solves this by providing a single place to upload, process, and review all communication artifacts organized by person.

## Core Concepts

### Space
A Space is a container representing one person or context. All media and conversations related to that person live inside their Space. Each Space has:
- Name, description, avatar (color-coded)
- A unified timeline of all items
- A chat view reconstructing conversations
- Stats (counts by content type)

### Content Types

| Type | Input | Processing | Output |
|------|-------|-----------|--------|
| Call Recording | Audio files (MP3, WAV, M4A, OGG) | Transcription via faster-whisper | Hinglish transcript with timestamps |
| Chat Screenshot | Image files (PNG, JPG) | OCR via PaddleOCR → chat parsing | Structured chat messages (sender, text, time) |
| Chat Screenshot Group | Multiple images | OCR + OpenCV stitching | Stitched image + reconstructed chat |
| Status Update | Video/Image (MP4, MOV, PNG, JPG) | Metadata extraction | Ordered gallery with platform badges |
| Other Media | Any image/video | None | Stored and displayed as-is |

### Timestamp Handling
- **Auto-detected:** Extracted from content via OCR (e.g., WhatsApp timestamps in screenshots)
- **User-provided:** Manual datetime input during or after upload (primary method since files come from Google Drive without EXIF)
- **Editable:** Any timestamp can be edited at any time; changes auto-re-sort the timeline
- Timestamp source is tracked: `auto_detected | user_provided | file_metadata`

## Features

### F1: Spaces Management
- Create, edit, delete spaces
- List all spaces with search
- Per-space stats (item counts by type)
- Avatar with selectable color

### F2: File Upload
- Drag & drop or click-to-browse upload
- Multi-file upload with per-file:
  - Content type selector (call/chat/status/media)
  - Datetime picker (date + time)
- Upload progress with real-time status updates
- Smart grouping: multiple chat screenshots uploaded together can be grouped for stitching

### F3: Call Recording Transcription
- Automatic transcription on upload using faster-whisper
- Hindi audio → Hinglish transcript
- Timestamped segments (clickable to seek audio)
- Searchable transcript text
- Audio player with waveform visualization
- GPU acceleration when available, CPU fallback

### F4: Screenshot OCR & Chat Reconstruction
- Automatic OCR on screenshot upload using PaddleOCR
- WhatsApp chat format parsing: extract sender, message, timestamp
- Display as chat bubbles (reconstructed conversation)
- Editable messages (correct OCR mistakes)
- GPU acceleration when available, CPU fallback

### F5: Screenshot Stitching
- Multiple screenshots → overlap detection → vertical stitch (OpenCV)
- Three-layer view:
  1. **Chat View** (default) — OCR-extracted chat bubbles
  2. **Stitched Image** — merged scrollable image
  3. **Original Screenshots** — individual uploads, reorderable
- Graceful fallback if stitching fails (keep originals)
- Re-stitch after reordering

### F6: Status Management
- Upload WhatsApp/Snapchat/Instagram status videos and images
- Platform badge assignment
- Editable timestamps with auto-reorder
- Gallery view with platform filtering
- Video playback and image lightbox

### F7: Unified Timeline View
- Chronological log of all items within a space
- Expandable inline previews:
  - Calls: audio player + transcript snippet
  - Chats: chat bubbles
  - Status: video/image thumbnail
  - Media: image thumbnail
- Filter by content type
- Search within space (transcripts, OCR text, metadata)

### F8: Chat View
- Toggle between Timeline and Chat view
- Merges ALL chat groups into one continuous conversation
- Non-chat items (calls, statuses) appear as inline markers
- Source indicators showing which screenshot group each section came from
- Read-only reconstructed view

### F9: Global Search
- Search across all spaces
- Full-text search over transcripts, OCR text, chat messages, space names
- Results grouped by space with type indicators
- Click result → navigate to item within its space

## Technical Architecture

### Stack

| Layer | Technology | License |
|-------|-----------|---------|
| Backend API | FastAPI (Python) | MIT |
| Database | PostgreSQL | PostgreSQL License |
| Task Queue | Celery + Redis | BSD |
| ASR | faster-whisper | MIT |
| OCR | PaddleOCR | Apache 2.0 |
| Image Processing | OpenCV | Apache 2.0 |
| Frontend | React + Vite + TypeScript | MIT |
| Containerization | Docker Compose | Apache 2.0 |
| File Storage | Local filesystem | - |

### Infrastructure
- All services run via Docker Compose
- No host installations required (except Docker itself)
- NVIDIA GPU optional — all ML workloads have CPU fallback
- Async processing via Celery workers with Redis broker
- WebSocket for real-time processing status updates
- Local filesystem for file storage (Docker volume mount)

### Hardware Requirements (Minimum)
- 4-core CPU, 8GB RAM
- 10GB disk for application + models
- Additional disk for stored media

### Target Hardware
- AMD Ryzen 32-core, 32GB RAM
- NVIDIA RTX 3070 (8GB VRAM) — optional, may be disabled
- Local SSD storage

## Non-Functional Requirements

- **Open Source:** All components must be open-source with permissive licenses
- **Zero Cost:** No paid APIs or services
- **Docker-Only:** Complete deployment via `docker compose up`
- **GPU Optional:** Every ML workload must gracefully fallback to CPU
- **Testable:** Unit tests and integration tests for all features
- **Product Ready:** Each milestone is independently deployable and usable

## UX Reference
See `wireframes.html` in project root for interactive UI wireframes covering all screens.
