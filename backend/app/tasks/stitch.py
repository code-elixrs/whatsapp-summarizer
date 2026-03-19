import logging
import os
import uuid

import cv2
import numpy as np
from celery import states
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.media_item import MediaItem, ProcessingStatus
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_engine = create_engine(settings.database_url_sync, echo=False)
_SessionLocal = sessionmaker(bind=_engine)


def _load_images(db: Session, group_id: uuid.UUID) -> list[tuple[MediaItem, np.ndarray]]:
    """Load all images in a group, sorted by group_order."""
    items = (
        db.query(MediaItem)
        .filter(MediaItem.group_id == group_id)
        .order_by(MediaItem.group_order.asc())
        .all()
    )
    if not items:
        return []

    results = []
    for item in items:
        path = os.path.join(settings.UPLOAD_DIR, item.file_path)
        if not os.path.exists(path):
            logger.warning("Image not found: %s", path)
            continue
        img = cv2.imread(path)
        if img is None:
            logger.warning("Could not read image: %s", path)
            continue
        results.append((item, img))

    return results


def _find_overlap(img_top: np.ndarray, img_bottom: np.ndarray) -> int:
    """Find the vertical overlap between two consecutive screenshots.

    Uses ORB feature matching to detect shared regions between the bottom
    of img_top and the top of img_bottom.

    Returns the number of pixels of overlap, or 0 if no overlap detected.
    """
    h_top, w_top = img_top.shape[:2]
    h_bottom, w_bottom = img_bottom.shape[:2]

    # Only search in the likely overlap region (bottom 40% of top, top 40% of bottom)
    search_height = min(int(h_top * 0.4), int(h_bottom * 0.4), 400)
    if search_height < 50:
        return 0

    region_top = img_top[h_top - search_height:, :]
    region_bottom = img_bottom[:search_height, :]

    # Resize to same width if different
    if w_top != w_bottom:
        region_bottom = cv2.resize(region_bottom, (w_top, search_height))

    # Convert to grayscale for feature matching
    gray_top = cv2.cvtColor(region_top, cv2.COLOR_BGR2GRAY)
    gray_bottom = cv2.cvtColor(region_bottom, cv2.COLOR_BGR2GRAY)

    # Use ORB feature detector
    orb = cv2.ORB_create(nfeatures=500)
    kp1, des1 = orb.detectAndCompute(gray_top, None)
    kp2, des2 = orb.detectAndCompute(gray_bottom, None)

    if des1 is None or des2 is None or len(kp1) < 5 or len(kp2) < 5:
        # Fallback: try template matching on horizontal strips
        return _template_match_overlap(gray_top, gray_bottom, search_height)

    # Match features using BFMatcher
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)

    if len(matches) < 5:
        return _template_match_overlap(gray_top, gray_bottom, search_height)

    # Sort by distance and take best matches
    matches = sorted(matches, key=lambda m: m.distance)[:50]

    # Calculate vertical shift from matched keypoints
    shifts = []
    for m in matches:
        y1 = kp1[m.queryIdx].pt[1]  # y in top region (relative to region_top)
        y2 = kp2[m.trainIdx].pt[1]  # y in bottom region (relative to region_bottom)
        # The overlap means: the bottom of region_top aligns with the top of region_bottom
        # y1 is distance from top of region_top, y2 is distance from top of region_bottom
        # If they match, the overlap is: search_height - y1 + y2
        # But we need: the position in the original image
        shift = search_height - y1 + y2
        if 10 < shift < search_height * 1.5:
            shifts.append(shift)

    if not shifts:
        return _template_match_overlap(gray_top, gray_bottom, search_height)

    # Use median shift as the overlap
    overlap = int(np.median(shifts))
    return min(overlap, search_height)


def _template_match_overlap(
    gray_top: np.ndarray, gray_bottom: np.ndarray, search_height: int
) -> int:
    """Fallback overlap detection using template matching on horizontal strips."""
    h_top = gray_top.shape[0]

    # Take a strip from the bottom of the top image and search for it in the bottom image
    strip_height = min(30, h_top // 4)

    best_overlap = 0
    best_score = 0.0

    for offset in range(0, h_top - strip_height, strip_height // 2):
        strip = gray_top[h_top - strip_height - offset: h_top - offset, :]
        if strip.shape[0] < strip_height or strip.shape[1] < 10:
            continue

        # Ensure template is smaller than the search image
        if strip.shape[0] >= gray_bottom.shape[0] or strip.shape[1] >= gray_bottom.shape[1]:
            continue

        result = cv2.matchTemplate(gray_bottom, strip, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > 0.7 and max_val > best_score:
            best_score = max_val
            # Overlap = distance from bottom of top image + where it was found in bottom
            best_overlap = offset + max_loc[1] + strip_height

    return best_overlap


def _stitch_images(
    images: list[np.ndarray],
    update_progress=None,
) -> tuple[np.ndarray, list[int], bool]:
    """Stitch a list of images vertically using detected overlaps.

    Returns:
        (stitched_image, overlaps_list, used_feature_matching)
        If feature matching fails for all pairs, falls back to simple concatenation.
    """
    if len(images) == 1:
        return images[0], [], True

    stitched = images[0]
    overlaps = []
    used_matching = False

    for i in range(1, len(images)):
        if update_progress:
            progress = 30 + int(50 * i / len(images))
            update_progress(progress, f"stitching_{i}_of_{len(images) - 1}")

        next_img = images[i]

        # Resize to same width if needed
        if stitch_width := stitched.shape[1]:
            if next_img.shape[1] != stitch_width:
                scale = stitch_width / next_img.shape[1]
                next_img = cv2.resize(
                    next_img,
                    (stitch_width, int(next_img.shape[0] * scale)),
                )

        overlap = _find_overlap(stitched, next_img)
        overlaps.append(overlap)

        if overlap > 10:
            used_matching = True
            # Blend the overlap region for smooth transition
            h_stitch = stitched.shape[0]
            new_part = next_img[overlap:]

            # Simple alpha blend in overlap zone
            blend_zone_stitch = stitched[h_stitch - overlap:, :]
            blend_zone_next = next_img[:overlap, :]

            if blend_zone_stitch.shape == blend_zone_next.shape:
                alpha = np.linspace(1, 0, overlap).reshape(-1, 1, 1)
                blended = (blend_zone_stitch * alpha + blend_zone_next * (1 - alpha)).astype(
                    np.uint8
                )
                stitched[h_stitch - overlap:] = blended

            stitched = np.vstack([stitched, new_part])
        else:
            # No overlap: simple vertical concatenation with a subtle divider
            divider = np.full((3, stitch_width, 3), 100, dtype=np.uint8)
            stitched = np.vstack([stitched, divider, next_img])

    return stitched, overlaps, used_matching


@celery_app.task(bind=True, name="stitch_screenshots", max_retries=2)
def stitch_screenshots(self, group_id: str, auto_ocr: bool = True):
    """Stitch grouped screenshots into a single image.

    Args:
        group_id: UUID of the group to stitch.
        auto_ocr: Whether to automatically run OCR on the stitched result.
    """
    group_uuid = uuid.UUID(group_id)

    # Store task mapping in Redis
    try:
        from redis import Redis
        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.set(f"stitch_task:{group_id}", self.request.id, ex=3600)
        redis_client.close()
    except Exception:
        logger.debug("Could not store stitch task mapping in Redis")

    db: Session = _SessionLocal()
    try:
        # Load all images in the group
        self.update_state(
            state="STITCHING",
            meta={"group_id": group_id, "progress": 5, "status": "loading_images"},
        )

        image_pairs = _load_images(db, group_uuid)
        if len(image_pairs) < 2:
            logger.error("Group %s has fewer than 2 images", group_id)
            return {"error": "Need at least 2 images to stitch"}

        items = [pair[0] for pair in image_pairs]
        images = [pair[1] for pair in image_pairs]

        # Update all items to processing
        for item in items:
            item.processing_status = ProcessingStatus.PROCESSING
        db.commit()

        self.update_state(
            state="STITCHING",
            meta={"group_id": group_id, "progress": 10, "status": "detecting_overlap"},
        )

        def update_progress(progress, status):
            self.update_state(
                state="STITCHING",
                meta={"group_id": group_id, "progress": progress, "status": status},
            )

        # Stitch
        stitched, overlaps, used_matching = _stitch_images(images, update_progress)

        self.update_state(
            state="STITCHING",
            meta={"group_id": group_id, "progress": 85, "status": "saving"},
        )

        # Save stitched image
        first_item = items[0]
        stitch_dir = os.path.dirname(
            os.path.join(settings.UPLOAD_DIR, first_item.file_path)
        )
        stitch_filename = f"stitched_{group_id}.png"
        stitch_relative = os.path.join(
            os.path.dirname(first_item.file_path), stitch_filename
        )
        stitch_absolute = os.path.join(settings.UPLOAD_DIR, stitch_relative)

        os.makedirs(os.path.dirname(stitch_absolute), exist_ok=True)
        cv2.imwrite(stitch_absolute, stitched)

        # Update all items with stitched_path
        for item in items:
            item.stitched_path = stitch_relative
            item.processing_status = ProcessingStatus.COMPLETED
        db.commit()

        self.update_state(
            state="STITCHING",
            meta={"group_id": group_id, "progress": 95, "status": "finalizing"},
        )

        result = {
            "group_id": group_id,
            "stitched_path": stitch_relative,
            "total_images": len(images),
            "overlaps": overlaps,
            "used_feature_matching": used_matching,
            "stitched_size": {
                "width": stitched.shape[1],
                "height": stitched.shape[0],
            },
        }

        # Auto-run OCR on the stitched image if requested
        if auto_ocr:
            try:
                from app.tasks.ocr import ocr_screenshot
                # Create a virtual media item for the stitched image, or run OCR
                # on the first item (which now has the stitched_path)
                # We'll run OCR task on the first item — it will read from stitched_path
                first_item.processing_status = ProcessingStatus.PENDING
                db.commit()
                ocr_task = ocr_screenshot.delay(str(first_item.id))
                result["ocr_task_id"] = ocr_task.id
                logger.info(
                    "Queued auto-OCR task %s for stitched group %s",
                    ocr_task.id, group_id,
                )
            except Exception:
                logger.exception("Failed to queue auto-OCR for group %s", group_id)

        logger.info(
            "Stitching complete for group %s: %d images, overlaps=%s",
            group_id, len(images), overlaps,
        )
        return result

    except Exception as exc:
        logger.exception("Stitching failed for group %s", group_id)
        try:
            items = (
                db.query(MediaItem)
                .filter(MediaItem.group_id == group_uuid)
                .all()
            )
            for item in items:
                item.processing_status = ProcessingStatus.FAILED
            db.commit()
        except Exception:
            db.rollback()

        self.update_state(
            state=states.FAILURE,
            meta={"group_id": group_id, "error": str(exc)},
        )
        raise
    finally:
        db.close()
