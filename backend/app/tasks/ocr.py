import json
import logging
import os
import re
import uuid
from datetime import datetime

from celery import states
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.chat_message import ChatMessage
from app.models.media_item import MediaItem, ProcessingStatus
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Sync engine for Celery tasks
_engine = create_engine(settings.database_url_sync, echo=False)
_SessionLocal = sessionmaker(bind=_engine)


def _detect_gpu() -> bool:
    """Check if GPU is available for PaddleOCR."""
    gpu_setting = settings.OCR_USE_GPU
    if gpu_setting == "true":
        return True
    if gpu_setting == "false":
        return False
    # auto-detect
    try:
        import paddle
        return paddle.device.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
    except Exception:
        return False


def _load_ocr():
    """Load PaddleOCR with GPU/CPU auto-detection."""
    from paddleocr import PaddleOCR

    use_gpu = _detect_gpu()
    model_dir = settings.OCR_MODEL_DIR
    os.makedirs(model_dir, exist_ok=True)

    logger.info("Loading PaddleOCR (use_gpu=%s, model_dir=%s)", use_gpu, model_dir)

    ocr = PaddleOCR(
        use_angle_cls=True,
        lang="en",
        use_gpu=use_gpu,
        det_model_dir=os.path.join(model_dir, "det"),
        rec_model_dir=os.path.join(model_dir, "rec"),
        cls_model_dir=os.path.join(model_dir, "cls"),
        show_log=False,
    )
    return ocr


def _parse_whatsapp_chat(ocr_results: list[dict]) -> list[dict]:
    """Parse OCR text blocks into structured WhatsApp chat messages.

    Uses spatial layout (bounding box positions) to determine:
    - Left-aligned messages = received (is_sent=False)
    - Right-aligned messages = sent (is_sent=True)

    Groups nearby text blocks into single messages and extracts timestamps.
    """
    if not ocr_results:
        return []

    # Sort blocks top-to-bottom by y-coordinate
    blocks = sorted(ocr_results, key=lambda b: b["y_center"])

    # Determine image width from bounding boxes to classify left/right
    all_x_centers = [b["x_center"] for b in blocks]
    if not all_x_centers:
        return []

    # Use the range of x positions to determine left vs right
    min_x = min(b["x_min"] for b in blocks)
    max_x = max(b["x_max"] for b in blocks)
    img_width = max_x - min_x if max_x > min_x else 1
    mid_x = min_x + img_width / 2

    # Timestamp patterns (WhatsApp formats)
    time_pattern = re.compile(
        r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)"  # 12h or 24h time
        r"|(\d{1,2}/\d{1,2}/\d{2,4},?\s*\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)"  # date + time
        r"|(\d{1,2}\.\d{2}\s*(?:AM|PM|am|pm)?)"  # time with dot separator
    )

    # Group text blocks into messages based on vertical proximity
    messages = []
    current_msg_blocks: list[dict] = []
    current_side: str | None = None

    # Vertical gap threshold for grouping (relative to avg text height)
    avg_height = sum(b["height"] for b in blocks) / len(blocks) if blocks else 20
    gap_threshold = avg_height * 1.5

    for block in blocks:
        block_side = "right" if block["x_center"] > mid_x else "left"

        if current_msg_blocks:
            last_block = current_msg_blocks[-1]
            vertical_gap = block["y_min"] - last_block["y_max"]

            # New message if: side changed, or large vertical gap
            if block_side != current_side or vertical_gap > gap_threshold:
                # Flush current message
                _flush_message(current_msg_blocks, current_side, messages, time_pattern)
                current_msg_blocks = []

        current_msg_blocks.append(block)
        current_side = block_side

    # Flush last message
    if current_msg_blocks:
        _flush_message(current_msg_blocks, current_side, messages, time_pattern)

    # Filter out very short messages that are likely UI elements
    messages = [m for m in messages if len(m["message"].strip()) > 0]

    return messages


def _flush_message(
    blocks: list[dict],
    side: str | None,
    messages: list[dict],
    time_pattern: re.Pattern,
) -> None:
    """Convert a group of text blocks into a single chat message."""
    full_text = " ".join(b["text"] for b in blocks)

    # Try to extract timestamp from the text
    timestamp_str = None
    time_match = time_pattern.search(full_text)
    if time_match:
        timestamp_str = time_match.group(0).strip()
        # Remove the timestamp from the message text
        clean_text = time_pattern.sub("", full_text).strip()
        # Clean up extra whitespace and punctuation left behind
        clean_text = re.sub(r"\s{2,}", " ", clean_text).strip(" ,-")
    else:
        clean_text = full_text.strip()

    if not clean_text:
        return

    # Try to extract sender name (typically "Name:" at start for group chats)
    sender = None
    sender_match = re.match(r"^([A-Za-z\s]+?):\s*(.+)", clean_text, re.DOTALL)
    if sender_match and len(sender_match.group(1)) < 30:
        sender = sender_match.group(1).strip()
        clean_text = sender_match.group(2).strip()

    # Parse timestamp
    parsed_timestamp = None
    if timestamp_str:
        parsed_timestamp = _parse_timestamp(timestamp_str)

    messages.append({
        "sender": sender,
        "message": clean_text,
        "timestamp_raw": timestamp_str,
        "timestamp": parsed_timestamp,
        "is_sent": side == "right",
    })


def _parse_timestamp(ts_str: str) -> str | None:
    """Best-effort parse of WhatsApp timestamp formats."""
    formats = [
        "%I:%M %p",
        "%I:%M%p",
        "%H:%M",
        "%I.%M %p",
        "%I.%M%p",
        "%m/%d/%y, %I:%M %p",
        "%m/%d/%Y, %I:%M %p",
        "%d/%m/%y, %I:%M %p",
        "%d/%m/%Y, %I:%M %p",
        "%m/%d/%y, %H:%M",
        "%d/%m/%y, %H:%M",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(ts_str.strip(), fmt)
            return dt.isoformat()
        except ValueError:
            continue
    return None


def _extract_ocr_blocks(result) -> list[dict]:
    """Convert PaddleOCR result to structured text blocks with positions."""
    blocks = []
    if not result:
        return blocks

    for line in result:
        if not line:
            continue
        for item in line:
            if len(item) < 2:
                continue
            bbox = item[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            text_info = item[1]  # (text, confidence)

            if not bbox or not text_info:
                continue

            text = text_info[0] if isinstance(text_info, (list, tuple)) else str(text_info)
            confidence = text_info[1] if isinstance(text_info, (list, tuple)) and len(text_info) > 1 else 0.0

            # Skip low-confidence results
            if confidence < 0.5:
                continue

            # Calculate bounding box metrics
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]

            blocks.append({
                "text": text,
                "confidence": confidence,
                "bbox": bbox,
                "x_min": min(xs),
                "x_max": max(xs),
                "y_min": min(ys),
                "y_max": max(ys),
                "x_center": sum(xs) / 4,
                "y_center": sum(ys) / 4,
                "width": max(xs) - min(xs),
                "height": max(ys) - min(ys),
            })

    return blocks


@celery_app.task(bind=True, name="ocr_screenshot", max_retries=2)
def ocr_screenshot(self, item_id: str):
    """Run OCR on a chat screenshot and parse into structured messages.

    Args:
        item_id: UUID of the MediaItem to process.
    """
    item_uuid = uuid.UUID(item_id)

    # Store task_id mapping in Redis for WebSocket lookup
    try:
        from redis import Redis
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.set(f"ocr_task:{item_id}", self.request.id, ex=3600)
        redis_client.close()
    except Exception:
        logger.debug("Could not store OCR task mapping in Redis")

    db: Session = _SessionLocal()
    try:
        item = db.get(MediaItem, item_uuid)
        if not item:
            logger.error("MediaItem %s not found", item_id)
            return {"error": "Item not found"}

        # Update status to processing
        item.processing_status = ProcessingStatus.PROCESSING
        db.commit()

        self.update_state(
            state="OCR_PROCESSING",
            meta={"item_id": item_id, "progress": 0, "status": "loading_model"},
        )

        # Load OCR model
        ocr = _load_ocr()

        self.update_state(
            state="OCR_PROCESSING",
            meta={"item_id": item_id, "progress": 20, "status": "running_ocr"},
        )

        # Get file path
        file_path = os.path.join(settings.UPLOAD_DIR, item.file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Screenshot not found: {file_path}")

        # Run OCR
        result = ocr.ocr(file_path, cls=True)

        self.update_state(
            state="OCR_PROCESSING",
            meta={"item_id": item_id, "progress": 60, "status": "extracting_text"},
        )

        # Extract text blocks with positions
        blocks = _extract_ocr_blocks(result)

        self.update_state(
            state="OCR_PROCESSING",
            meta={"item_id": item_id, "progress": 70, "status": "parsing_chat"},
        )

        # Parse into chat messages
        messages = _parse_whatsapp_chat(blocks)

        self.update_state(
            state="OCR_PROCESSING",
            meta={"item_id": item_id, "progress": 85, "status": "saving"},
        )

        # Delete existing messages if re-processing
        db.query(ChatMessage).filter(ChatMessage.media_item_id == item_uuid).delete()
        db.flush()

        # Save messages
        for i, msg in enumerate(messages):
            db.add(ChatMessage(
                media_item_id=item_uuid,
                sender=msg.get("sender"),
                message=msg["message"],
                message_timestamp=datetime.fromisoformat(msg["timestamp"]) if msg.get("timestamp") else None,
                message_order=i,
                is_sent=msg.get("is_sent", False),
            ))

        item.processing_status = ProcessingStatus.COMPLETED
        db.commit()

        # Save raw OCR output as JSON
        raw_output_path = file_path + ".ocr.json"
        # Convert blocks to serializable format
        serializable_blocks = []
        for b in blocks:
            sb = {k: v for k, v in b.items() if k != "bbox"}
            sb["bbox"] = [[float(p[0]), float(p[1])] for p in b["bbox"]]
            serializable_blocks.append(sb)

        with open(raw_output_path, "w") as f:
            json.dump({
                "blocks": serializable_blocks,
                "messages": messages,
                "total_blocks": len(blocks),
                "total_messages": len(messages),
            }, f, indent=2, default=str)

        result_data = {
            "item_id": item_id,
            "total_blocks": len(blocks),
            "total_messages": len(messages),
            "messages_preview": [m["message"][:50] for m in messages[:5]],
        }

        logger.info(
            "OCR complete for %s: %d blocks → %d messages",
            item_id, len(blocks), len(messages),
        )
        return result_data

    except Exception as exc:
        logger.exception("OCR failed for %s", item_id)
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
