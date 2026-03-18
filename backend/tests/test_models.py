import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, MediaItem, Space, Transcript, TranscriptSegment
from app.models.media_item import ContentType, ProcessingStatus, TimestampSource


@pytest.mark.asyncio
async def test_create_space(db_session: AsyncSession):
    space = Space(name="Test Person", description="A test space", color="#7c3aed")
    db_session.add(space)
    await db_session.flush()

    assert space.id is not None
    assert space.name == "Test Person"
    assert space.created_at is not None


@pytest.mark.asyncio
async def test_create_media_item(db_session: AsyncSession):
    space = Space(name="Test Person", color="#7c3aed")
    db_session.add(space)
    await db_session.flush()

    item = MediaItem(
        space_id=space.id,
        content_type=ContentType.CALL_RECORDING,
        file_path="/uploads/test.mp3",
        file_name="test.mp3",
        file_size=1024,
        mime_type="audio/mpeg",
        item_timestamp=datetime.now(timezone.utc),
        timestamp_source=TimestampSource.USER_PROVIDED,
        processing_status=ProcessingStatus.PENDING,
    )
    db_session.add(item)
    await db_session.flush()

    assert item.id is not None
    assert item.space_id == space.id
    assert item.content_type == ContentType.CALL_RECORDING


@pytest.mark.asyncio
async def test_create_transcript_with_segments(db_session: AsyncSession):
    space = Space(name="Test Person", color="#7c3aed")
    db_session.add(space)
    await db_session.flush()

    item = MediaItem(
        space_id=space.id,
        content_type=ContentType.CALL_RECORDING,
        file_path="/uploads/test.mp3",
        file_name="test.mp3",
        file_size=1024,
        mime_type="audio/mpeg",
    )
    db_session.add(item)
    await db_session.flush()

    transcript = Transcript(
        media_item_id=item.id,
        full_text="Hello world",
        language="hi",
    )
    db_session.add(transcript)
    await db_session.flush()

    segment = TranscriptSegment(
        transcript_id=transcript.id,
        start_time=0.0,
        end_time=2.5,
        text="Hello world",
        segment_index=0,
    )
    db_session.add(segment)
    await db_session.flush()

    assert transcript.id is not None
    assert segment.transcript_id == transcript.id


@pytest.mark.asyncio
async def test_create_chat_message(db_session: AsyncSession):
    space = Space(name="Test Person", color="#7c3aed")
    db_session.add(space)
    await db_session.flush()

    item = MediaItem(
        space_id=space.id,
        content_type=ContentType.CHAT_SCREENSHOT,
        file_path="/uploads/chat.png",
        file_name="chat.png",
        file_size=2048,
        mime_type="image/png",
    )
    db_session.add(item)
    await db_session.flush()

    msg = ChatMessage(
        media_item_id=item.id,
        sender="Rahul",
        message="Hello bhai",
        message_order=0,
        is_sent=False,
    )
    db_session.add(msg)
    await db_session.flush()

    assert msg.id is not None
    assert msg.sender == "Rahul"
