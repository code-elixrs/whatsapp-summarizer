import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.media_item import ContentType, MediaItem
from app.models.space import Space
from app.schemas.space import (
    SpaceCreate,
    SpaceItemCounts,
    SpaceListResponse,
    SpaceResponse,
    SpaceUpdate,
)

router = APIRouter(prefix="/spaces", tags=["spaces"])


async def _get_item_counts(db: AsyncSession, space_id: uuid.UUID) -> SpaceItemCounts:
    result = await db.execute(
        select(MediaItem.content_type, func.count())
        .where(MediaItem.space_id == space_id)
        .group_by(MediaItem.content_type)
    )
    counts = {row[0]: row[1] for row in result.all()}
    return SpaceItemCounts(
        calls=counts.get(ContentType.CALL_RECORDING, 0),
        chats=counts.get(ContentType.CHAT_SCREENSHOT, 0),
        statuses=counts.get(ContentType.STATUS_UPDATE, 0),
        media=counts.get(ContentType.OTHER_MEDIA, 0),
    )


async def _space_to_response(db: AsyncSession, space: Space) -> SpaceResponse:
    item_counts = await _get_item_counts(db, space.id)
    return SpaceResponse(
        id=space.id,
        name=space.name,
        description=space.description,
        color=space.color,
        created_at=space.created_at,
        updated_at=space.updated_at,
        item_counts=item_counts,
    )


@router.post("", response_model=SpaceResponse, status_code=201)
async def create_space(data: SpaceCreate, db: AsyncSession = Depends(get_db)):
    space = Space(name=data.name, description=data.description, color=data.color)
    db.add(space)
    await db.commit()
    await db.refresh(space)
    return await _space_to_response(db, space)


@router.get("", response_model=SpaceListResponse)
async def list_spaces(
    search: str | None = Query(default=None, max_length=255),
    db: AsyncSession = Depends(get_db),
):
    query = select(Space).order_by(Space.updated_at.desc())
    if search:
        query = query.where(Space.name.ilike(f"%{search}%"))

    result = await db.execute(query)
    spaces = result.scalars().all()

    responses = [await _space_to_response(db, s) for s in spaces]
    return SpaceListResponse(spaces=responses, total=len(responses))


@router.get("/{space_id}", response_model=SpaceResponse)
async def get_space(space_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    space = await db.get(Space, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    return await _space_to_response(db, space)


@router.put("/{space_id}", response_model=SpaceResponse)
async def update_space(
    space_id: uuid.UUID, data: SpaceUpdate, db: AsyncSession = Depends(get_db)
):
    space = await db.get(Space, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(space, field, value)

    await db.commit()
    await db.refresh(space)
    return await _space_to_response(db, space)


@router.delete("/{space_id}", status_code=204)
async def delete_space(space_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    space = await db.get(Space, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    await db.delete(space)
    await db.commit()
