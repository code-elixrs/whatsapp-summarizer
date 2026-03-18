import mimetypes
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import delete_file, generate_file_path, get_absolute_path, save_upload
from app.models.media_item import ContentType, MediaItem, ProcessingStatus, TimestampSource
from app.models.space import Space
from app.schemas.media_item import (
    MediaItemListResponse,
    MediaItemResponse,
    MediaItemUpdate,
)

router = APIRouter(tags=["items"])

ALLOWED_MIME_PREFIXES = ("image/", "audio/", "video/")
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


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

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 500MB)")

    relative_path, absolute_path = generate_file_path(space_id, file.filename)
    await save_upload(content, absolute_path)

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
        processing_status=ProcessingStatus.COMPLETED,
        group_id=group_id,
        group_order=group_order,
        platform=platform,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
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
