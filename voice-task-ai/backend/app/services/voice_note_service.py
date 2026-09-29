"""
Handles safe storage of uploaded audio files.

Security measures:
- Extension allow-list (checked against the actual filename extension,
  not just the browser-supplied content type).
- Size limit enforced via settings.MAX_UPLOAD_SIZE_MB.
- Filenames are never trusted: we generate our own UUID-based filename,
  so path traversal (e.g. "../../evil.sh") and collisions are impossible.
"""
import os
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException, status

from app.config import settings


class InvalidAudioFile(Exception):
    """Non-HTTP counterpart to the upload endpoint's validation errors —
    used by the inbox watcher, which runs outside any HTTP request."""


def _validate_extension(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Allowed types: {', '.join(sorted(settings.ALLOWED_AUDIO_EXTENSIONS))}"
            ),
        )
    return ext


def save_audio_file(upload: UploadFile) -> tuple[str, int]:
    """
    Validates and saves an uploaded audio file to disk.
    Returns (relative_path, size_in_bytes).
    Raises HTTPException on invalid file type, empty file, or oversized file.
    """
    if not upload.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided.")

    ext = _validate_extension(upload.filename)

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = upload_dir / safe_name

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    size = 0

    try:
        with open(dest_path, "wb") as out_file:
            while chunk := upload.file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    out_file.close()
                    os.remove(dest_path)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit.",
                    )
                out_file.write(chunk)
    finally:
        upload.file.close()

    if size == 0:
        os.remove(dest_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    return str(dest_path), size


def ingest_local_file(source_path: Path) -> tuple[str, int]:
    """
    Same validation/storage logic as save_audio_file, but for a file that
    already exists on disk (used by the inbox watcher) rather than an
    HTTP UploadFile. Copies — never moves — the source, so the watcher
    never risks deleting something from a folder it doesn't own (e.g.
    WhatsApp Desktop's own media folder).

    Raises InvalidAudioFile instead of HTTPException, since this runs
    outside any HTTP request context.
    """
    ext = source_path.suffix.lower()
    if ext not in settings.ALLOWED_AUDIO_EXTENSIONS:
        raise InvalidAudioFile(f"Unsupported file type '{ext}'.")

    size = source_path.stat().st_size
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size == 0:
        raise InvalidAudioFile("File is empty.")
    if size > max_bytes:
        raise InvalidAudioFile(f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB limit.")

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = upload_dir / safe_name
    shutil.copy2(source_path, dest_path)

    return str(dest_path), size
