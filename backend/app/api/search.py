import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.space import Space
from app.schemas.search import SearchResponse, SearchResultItem

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def global_search(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across all spaces: chat messages, transcripts, and media items."""
    results = await _search(db, q, limit=limit)
    return SearchResponse(query=q, results=results, total=len(results))


@router.get("/spaces/{space_id}/search", response_model=SearchResponse)
async def space_search(
    space_id: uuid.UUID,
    q: str = Query(..., min_length=1, max_length=500),
    content_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search within a specific space with optional content type filter."""
    space = await db.get(Space, space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")

    results = await _search(db, q, space_id=space_id, content_type=content_type, limit=limit)
    return SearchResponse(query=q, results=results, total=len(results))


async def _search(
    db: AsyncSession,
    query: str,
    space_id: uuid.UUID | None = None,
    content_type: str | None = None,
    limit: int = 50,
) -> list[SearchResultItem]:
    """Run full-text search across chat_messages, transcripts, and media_items."""

    tsquery = "plainto_tsquery('english', :query)"
    space_filter = "AND mi.space_id = :space_id" if space_id else ""
    type_filter = "AND mi.content_type::text = :content_type" if content_type else ""

    sql = text(f"""
    (
        SELECT
            'chat_message' AS result_type,
            mi.id AS item_id,
            mi.space_id,
            s.name AS space_name,
            mi.content_type::text,
            mi.title,
            mi.file_name,
            ts_headline('english', cm.message, {tsquery},
                'MaxWords=30, MinWords=15, StartSel=**, StopSel=**') AS snippet,
            mi.item_timestamp,
            mi.platform,
            ts_rank(to_tsvector('english', coalesce(cm.sender, '') || ' ' || cm.message), {tsquery}) AS rank
        FROM chat_messages cm
        JOIN media_items mi ON cm.media_item_id = mi.id
        JOIN spaces s ON mi.space_id = s.id
        WHERE to_tsvector('english', coalesce(cm.sender, '') || ' ' || cm.message) @@ {tsquery}
        {space_filter} {type_filter}
    )
    UNION ALL
    (
        SELECT
            'transcript' AS result_type,
            mi.id AS item_id,
            mi.space_id,
            s.name AS space_name,
            mi.content_type::text,
            mi.title,
            mi.file_name,
            ts_headline('english', t.full_text, {tsquery},
                'MaxWords=30, MinWords=15, StartSel=**, StopSel=**') AS snippet,
            mi.item_timestamp,
            mi.platform,
            ts_rank(to_tsvector('english', t.full_text), {tsquery}) AS rank
        FROM transcripts t
        JOIN media_items mi ON t.media_item_id = mi.id
        JOIN spaces s ON mi.space_id = s.id
        WHERE to_tsvector('english', t.full_text) @@ {tsquery}
        {space_filter} {type_filter}
    )
    UNION ALL
    (
        SELECT
            'media_item' AS result_type,
            mi.id AS item_id,
            mi.space_id,
            s.name AS space_name,
            mi.content_type::text,
            mi.title,
            mi.file_name,
            ts_headline('english',
                coalesce(mi.title, '') || ' ' || coalesce(mi.notes, '') || ' ' || mi.file_name,
                {tsquery},
                'MaxWords=30, MinWords=15, StartSel=**, StopSel=**') AS snippet,
            mi.item_timestamp,
            mi.platform,
            ts_rank(to_tsvector('english',
                coalesce(mi.title, '') || ' ' || coalesce(mi.notes, '') || ' ' || mi.file_name
            ), {tsquery}) AS rank
        FROM media_items mi
        JOIN spaces s ON mi.space_id = s.id
        WHERE to_tsvector('english',
            coalesce(mi.title, '') || ' ' || coalesce(mi.notes, '') || ' ' || mi.file_name
        ) @@ {tsquery}
        {space_filter} {type_filter}
    )
    ORDER BY rank DESC
    LIMIT :limit
    """)

    params: dict = {"query": query, "limit": limit}
    if space_id:
        params["space_id"] = space_id
    if content_type:
        params["content_type"] = content_type

    result = await db.execute(sql, params)
    rows = result.fetchall()

    return [
        SearchResultItem(
            result_type=row.result_type,
            item_id=row.item_id,
            space_id=row.space_id,
            space_name=row.space_name,
            content_type=row.content_type,
            title=row.title,
            file_name=row.file_name,
            snippet=row.snippet,
            item_timestamp=row.item_timestamp,
            platform=row.platform,
        )
        for row in rows
    ]
