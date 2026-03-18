import os
import uuid
from pathlib import Path

import aiofiles

from app.core.config import settings


def get_upload_dir(space_id: uuid.UUID) -> Path:
    path = Path(settings.UPLOAD_DIR) / str(space_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def generate_file_path(space_id: uuid.UUID, original_filename: str) -> tuple[str, str]:
    """Returns (relative_path, absolute_path) for a new upload."""
    ext = Path(original_filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    relative = f"{space_id}/{unique_name}"
    absolute = str(Path(settings.UPLOAD_DIR) / relative)
    return relative, absolute


async def save_upload(file_content: bytes, absolute_path: str) -> None:
    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
    async with aiofiles.open(absolute_path, "wb") as f:
        await f.write(file_content)


def delete_file(relative_path: str) -> None:
    absolute = Path(settings.UPLOAD_DIR) / relative_path
    if absolute.is_file():
        absolute.unlink()


def get_absolute_path(relative_path: str) -> str:
    return str(Path(settings.UPLOAD_DIR) / relative_path)
