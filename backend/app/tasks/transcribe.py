import json
import logging
import os
import uuid

from celery import states
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.media_item import MediaItem, ProcessingStatus
from app.models.transcript import Transcript, TranscriptSegment
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Sync engine for Celery tasks (Celery is sync, not async)
_engine = create_engine(settings.database_url_sync, echo=False)
_SessionLocal = sessionmaker(bind=_engine)


def _get_device_and_compute():
    """Auto-detect CUDA availability and return (device, compute_type)."""
    device = settings.WHISPER_DEVICE
    compute_type = settings.WHISPER_COMPUTE_TYPE

    if device == "auto":
        try:
            import ctranslate2
            if "cuda" in ctranslate2.get_supported_compute_types("cuda"):
                device = "cuda"
                if compute_type == "auto":
                    compute_type = "float16"
                logger.info("CUDA detected, using GPU with %s", compute_type)
            else:
                raise RuntimeError("No CUDA")
        except Exception:
            device = "cpu"
            if compute_type == "auto":
                compute_type = "int8"
            logger.info("No CUDA available, using CPU with %s", compute_type)
    elif device == "cuda":
        if compute_type == "auto":
            compute_type = "float16"
    else:
        if compute_type == "auto":
            compute_type = "int8"

    return device, compute_type


def _load_model(model_size: str):
    """Load or retrieve cached whisper model."""
    from faster_whisper import WhisperModel

    device, compute_type = _get_device_and_compute()
    model_dir = settings.WHISPER_MODEL_DIR
    os.makedirs(model_dir, exist_ok=True)

    logger.info(
        "Loading whisper model '%s' (device=%s, compute_type=%s, cache=%s)",
        model_size, device, compute_type, model_dir,
    )
    return WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        download_root=model_dir,
    )


@celery_app.task(bind=True, name="transcribe_audio", max_retries=2)
def transcribe_audio(self, item_id: str, model_size: str | None = None):
    """Transcribe an audio file using faster-whisper.

    Args:
        item_id: UUID of the MediaItem to transcribe.
        model_size: Whisper model size (tiny, base, small, medium, large-v3).
                    Defaults to WHISPER_DEFAULT_MODEL from settings.
    """
    model_size = model_size or settings.WHISPER_DEFAULT_MODEL
    item_uuid = uuid.UUID(item_id)

    # Store task_id mapping in Redis so WebSocket can find it
    try:
        from redis import Redis
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.set(f"transcription_task:{item_id}", self.request.id, ex=3600)
        redis_client.close()
    except Exception:
        logger.debug("Could not store task mapping in Redis")

    db: Session = _SessionLocal()
    try:
        item = db.get(MediaItem, item_uuid)
        if not item:
            logger.error("MediaItem %s not found", item_id)
            return {"error": "Item not found"}

        # Update status to processing
        item.processing_status = ProcessingStatus.PROCESSING
        db.commit()

        # Notify progress via task state
        self.update_state(
            state="TRANSCRIBING",
            meta={"item_id": item_id, "progress": 0, "status": "loading_model"},
        )

        # Check device — warn if user requested GPU but CUDA unavailable
        device, compute_type = _get_device_and_compute()
        gpu_warning = None
        if settings.WHISPER_DEVICE == "cuda" and device == "cpu":
            gpu_warning = "GPU requested but CUDA not available, falling back to CPU"
            logger.warning(gpu_warning)

        # Load model
        model = _load_model(model_size)

        self.update_state(
            state="TRANSCRIBING",
            meta={"item_id": item_id, "progress": 10, "status": "transcribing"},
        )

        # Get absolute file path
        file_path = os.path.join(settings.UPLOAD_DIR, item.file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        # Transcribe — language=None for auto-detect
        segments_iter, info = model.transcribe(
            file_path,
            language=None,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        # Collect segments
        all_segments = []
        for i, segment in enumerate(segments_iter):
            all_segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            })
            # Update progress (estimate based on segment count)
            progress = min(10 + int(80 * (i + 1) / max(i + 2, 10)), 90)
            self.update_state(
                state="TRANSCRIBING",
                meta={
                    "item_id": item_id,
                    "progress": progress,
                    "status": "transcribing",
                    "segments_done": i + 1,
                },
            )

        full_text = " ".join(s["text"] for s in all_segments)

        self.update_state(
            state="TRANSCRIBING",
            meta={"item_id": item_id, "progress": 95, "status": "saving"},
        )

        # Delete existing transcript if re-transcribing
        existing = db.query(Transcript).filter(
            Transcript.media_item_id == item_uuid
        ).first()
        if existing:
            db.delete(existing)
            db.flush()

        # Save transcript
        transcript = Transcript(
            media_item_id=item_uuid,
            full_text=full_text,
            language=info.language,
        )
        db.add(transcript)
        db.flush()

        # Save segments
        for i, seg in enumerate(all_segments):
            db.add(TranscriptSegment(
                transcript_id=transcript.id,
                start_time=seg["start"],
                end_time=seg["end"],
                text=seg["text"],
                segment_index=i,
            ))

        # Update media item
        item.processing_status = ProcessingStatus.COMPLETED
        item.duration_seconds = int(info.duration) if info.duration else None
        db.commit()

        result = {
            "item_id": item_id,
            "transcript_id": str(transcript.id),
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments_count": len(all_segments),
            "full_text_preview": full_text[:200],
            "model_size": model_size,
            "device": device,
            "compute_type": compute_type,
        }
        if gpu_warning:
            result["gpu_warning"] = gpu_warning

        # Save raw output as JSON alongside the audio file
        raw_output_path = file_path + ".whisper.json"
        with open(raw_output_path, "w") as f:
            json.dump({
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "model_size": model_size,
                "segments": all_segments,
            }, f, indent=2)

        logger.info(
            "Transcription complete for %s: %d segments, language=%s",
            item_id, len(all_segments), info.language,
        )
        return result

    except Exception as exc:
        logger.exception("Transcription failed for %s", item_id)
        # Update status to failed
        try:
            item = db.get(MediaItem, item_uuid)
            if item:
                item.processing_status = ProcessingStatus.FAILED
                db.commit()
        except Exception:
            db.rollback()

        self.update_state(
            state=states.FAILURE,
            meta={"item_id": item_id, "error": str(exc)},
        )
        raise
    finally:
        db.close()
