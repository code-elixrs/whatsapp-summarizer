import logging
import mimetypes
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.storage import delete_file, generate_file_path, get_absolute_path, save_upload
from app.models.media_item import ContentType, MediaItem, ProcessingStatus, TimestampSource
from app.models.space import Space
from app.models.chat_message import ChatMessage
from app.models.transcript import Transcript, TranscriptSegment
from app.schemas.chat_message import ChatMessageResponse, ChatMessageUpdate, ChatMessagesResponse
from app.schemas.media_item import (
    MediaItemListResponse,
    MediaItemResponse,
    MediaItemUpdate,
)
from app.schemas.transcript import TranscriptResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["items"])

ALLOWED_MIME_PREFIXES = ("image/", "audio/", "video/")
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
VALID_WHISPER_MODELS = ("tiny", "base", "small", "medium", "large-v3")


def _item_to_response(item: MediaItem) -> MediaItemResponse:
    return MediaItemResponse(
        id=item.id,
        space_id=item.space_id,
        content_type=item.content_type,
        title=item.title,
        notes=item.notes,
        file_name=item.file_name,
        file_size=item.file_size,
        mime_type=item.mime_type,
        item_timestamp=item.item_timestamp,
        timestamp_source=item.timestamp_source,
        processing_status=item.processing_status,
        group_id=item.group_id,
        group_order=item.group_order,
        stitched_path=item.stitched_path,
        platform=item.platform,
        duration_seconds=item.duration_seconds,
        created_at=item.created_at,
        updated_at=item.updated_at,
        file_url=f"/api/files/{item.id}",
    )


@router.post("/spaces/{space_id}/upload", response_model=MediaItemResponse, status_code=201)
async def upload_file(
    space_id: uuid.UUID,
    file: UploadFile = File(...),
    content_type: ContentType = Form(...),
    item_timestamp: datetime | None = Form(default=None),
    title: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    platform: str | None = Form(default=None),
    group_id: uuid.UUID | None = Form(default=None),
    group_order: int | None = Form(default=None),
    whisper_model: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    space = await db.get(Space, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")

    mime = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"
    if not any(mime.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {mime}")

    if whisper_model and whisper_model not in VALID_WHISPER_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid whisper model. Choose from: {', '.join(VALID_WHISPER_MODELS)}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 500MB)")

    relative_path, absolute_path = generate_file_path(space_id, file.filename)
    await save_upload(content, absolute_path)

    is_audio = mime.startswith("audio/")
    is_chat_screenshot = content_type == ContentType.CHAT_SCREENSHOT and mime.startswith("image/")
    needs_processing = is_audio or is_chat_screenshot

    item = MediaItem(
        space_id=space_id,
        content_type=content_type,
        title=title,
        notes=notes,
        file_path=relative_path,
        file_name=file.filename,
        file_size=len(content),
        mime_type=mime,
        item_timestamp=item_timestamp,
        timestamp_source=TimestampSource.USER_PROVIDED if item_timestamp else TimestampSource.USER_PROVIDED,
        processing_status=ProcessingStatus.PENDING if needs_processing else ProcessingStatus.COMPLETED,
        group_id=group_id,
        group_order=group_order,
        platform=platform,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    # Trigger async transcription for audio files
    if is_audio:
        from app.tasks.transcribe import transcribe_audio
        task = transcribe_audio.delay(str(item.id), whisper_model)
        logger.info("Queued transcription task %s for item %s", task.id, item.id)

    # Trigger async OCR for chat screenshots
    if is_chat_screenshot:
        from app.tasks.ocr import ocr_screenshot
        task = ocr_screenshot.delay(str(item.id))
        logger.info("Queued OCR task %s for item %s", task.id, item.id)

    return _item_to_response(item)


@router.get("/spaces/{space_id}/items", response_model=MediaItemListResponse)
async def list_items(
    space_id: uuid.UUID,
    content_type: ContentType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    space = await db.get(Space, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    query = select(MediaItem).where(MediaItem.space_id == space_id)
    count_query = select(func.count()).select_from(MediaItem).where(MediaItem.space_id == space_id)

    if content_type:
        query = query.where(MediaItem.content_type == content_type)
        count_query = count_query.where(MediaItem.content_type == content_type)

    # Sort: items with timestamps first (newest first), then by created_at
    query = query.order_by(
        MediaItem.item_timestamp.desc().nullslast(),
        MediaItem.created_at.desc(),
    )

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return MediaItemListResponse(
        items=[_item_to_response(i) for i in items],
        total=total,
    )


@router.get("/items/{item_id}", response_model=MediaItemResponse)
async def get_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    item = await db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return _item_to_response(item)


@router.put("/items/{item_id}", response_model=MediaItemResponse)
async def update_item(
    item_id: uuid.UUID,
    data: MediaItemUpdate,
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return _item_to_response(item)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    item = await db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    delete_file(item.file_path)
    await db.delete(item)
    await db.commit()


@router.get("/files/{item_id}")
async def serve_file(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    item = await db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    absolute_path = get_absolute_path(item.file_path)
    return FileResponse(
        path=absolute_path,
        media_type=item.mime_type,
        filename=item.file_name,
    )


@router.get("/items/{item_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    item = await db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    result = await db.execute(
        select(Transcript)
        .where(Transcript.media_item_id == item_id)
        .options(selectinload(Transcript.segments))
    )
    transcript = result.scalar_one_or_none()
    if not transcript:
        raise HTTPException(status_code=404, detail="No transcript found for this item")

    return TranscriptResponse.from_model(transcript)


@router.post("/items/{item_id}/transcribe", response_model=MediaItemResponse)
async def retranscribe_item(
    item_id: uuid.UUID,
    whisper_model: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Re-trigger transcription for an audio item (e.g., with a different model)."""
    item = await db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item.mime_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Only audio items can be transcribed")

    if whisper_model and whisper_model not in VALID_WHISPER_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid whisper model. Choose from: {', '.join(VALID_WHISPER_MODELS)}",
        )

    item.processing_status = ProcessingStatus.PENDING
    await db.commit()
    await db.refresh(item)

    from app.tasks.transcribe import transcribe_audio
    task = transcribe_audio.delay(str(item.id), whisper_model)
    logger.info("Queued re-transcription task %s for item %s", task.id, item.id)

    return _item_to_response(item)


@router.get("/items/{item_id}/transcription-status")
async def get_transcription_status(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get the current transcription/OCR task status for an item."""
    item = await db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return {
        "item_id": str(item.id),
        "processing_status": item.processing_status.value,
    }


@router.get("/items/{item_id}/chat-messages", response_model=ChatMessagesResponse)
async def get_chat_messages(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get parsed chat messages for a screenshot item."""
    item = await db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.media_item_id == item_id)
        .order_by(ChatMessage.message_order)
    )
    messages = result.scalars().all()

    return ChatMessagesResponse(
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
        total=len(messages),
    )


@router.put("/items/{item_id}/chat-messages/{message_id}", response_model=ChatMessageResponse)
async def update_chat_message(
    item_id: uuid.UUID,
    message_id: uuid.UUID,
    data: ChatMessageUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Edit a chat message (correct OCR errors)."""
    msg = await db.get(ChatMessage, message_id)
    if not msg or msg.media_item_id != item_id:
        raise HTTPException(status_code=404, detail="Message not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(msg, field, value)

    await db.commit()
    await db.refresh(msg)
    return ChatMessageResponse.model_validate(msg)


@router.post("/items/{item_id}/ocr", response_model=MediaItemResponse)
async def rerun_ocr(item_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Re-trigger OCR for a chat screenshot item."""
    item = await db.get(MediaItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item.mime_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image items can be OCR-processed")

    item.processing_status = ProcessingStatus.PENDING
    await db.commit()
    await db.refresh(item)

    from app.tasks.ocr import ocr_screenshot
    task = ocr_screenshot.delay(str(item.id))
    logger.info("Queued re-OCR task %s for item %s", task.id, item.id)

    return _item_to_response(item)
