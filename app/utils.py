"""Small helpers: image upload, simple rate limiting, text helpers."""
import io
import os
import time
import uuid
from collections import defaultdict

from fastapi import UploadFile, HTTPException
from PIL import Image

from .config import settings, UPLOADS_DIR

UPLOAD_DIR = str(UPLOADS_DIR / "packages")
try:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
except OSError:
    pass  # read-only filesystem (serverless) — see notes on persistent storage


def save_package_image(file: UploadFile) -> str:
    """Validate, lightly compress and save one uploaded image.

    Returns the public path (e.g. "/uploads/packages/ab12.jpg") to store in DB.
    """
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "Only JPG, PNG or WEBP images are allowed.")

    data = file.file.read()
    if len(data) > settings.MAX_IMAGE_MB * 1024 * 1024:
        raise HTTPException(400, f"Image must be under {settings.MAX_IMAGE_MB} MB.")

    try:
        img = Image.open(io.BytesIO(data))
        img.verify()  # confirm it is a real image
        img = Image.open(io.BytesIO(data))  # reopen after verify
    except Exception:
        raise HTTPException(400, "That file is not a valid image.")

    # Convert to RGB JPEG, cap the longest side to keep pages fast.
    img = img.convert("RGB")
    img.thumbnail((1600, 1600))
    name = f"{uuid.uuid4().hex}.jpg"
    path = os.path.join(UPLOAD_DIR, name)
    img.save(path, "JPEG", quality=82, optimize=True)
    return f"/uploads/packages/{name}"


def delete_image_file(public_path: str) -> None:
    """Remove an image file from disk, ignoring if already gone."""
    if not public_path:
        return
    local = public_path.lstrip("/")
    try:
        os.remove(local)
    except OSError:
        pass


# ---- Very simple in-memory rate limiter for the public enquiry form --------
_hits: dict[str, list[float]] = defaultdict(list)


def too_many_submissions(ip: str, limit: int = 6, window_sec: int = 600) -> bool:
    """Allow at most `limit` enquiries per IP per `window_sec` (default 10 min)."""
    now = time.time()
    recent = [t for t in _hits[ip] if now - t < window_sec]
    _hits[ip] = recent
    if len(recent) >= limit:
        return True
    _hits[ip].append(now)
    return False


def lines_to_list(text: str | None) -> list[str]:
    """Split a textarea value into clean bullet items (one per line)."""
    if not text:
        return []
    return [line.strip(" -•\t") for line in text.splitlines() if line.strip()]
