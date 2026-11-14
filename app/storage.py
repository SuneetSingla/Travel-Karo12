"""Image storage — Supabase Storage in production, local disk for dev.

Backend is chosen automatically:
  • If SUPABASE_URL + SUPABASE_SERVICE_KEY + SUPABASE_BUCKET are set
      -> images are uploaded to Supabase Storage; the public URL is stored in DB.
  • Otherwise (e.g. local development with no Supabase vars)
      -> images are saved to the local uploads/ folder and served from /uploads.

SECURITY: SUPABASE_SERVICE_KEY is used only here, server-side, in outbound
requests to Supabase. It is never rendered into a template or sent to the
browser, and never committed (it lives in .env / host env vars).
"""
import io
import os
import uuid
import logging

import httpx
from fastapi import UploadFile, HTTPException
from PIL import Image

from .config import settings, UPLOADS_DIR

log = logging.getLogger("travelkaro.storage")

LOCAL_DIR = str(UPLOADS_DIR / "packages")
try:
    os.makedirs(LOCAL_DIR, exist_ok=True)
except OSError:
    pass  # read-only filesystem (serverless) — Supabase backend is used there

_HTTP_TIMEOUT = httpx.Timeout(20.0)


# ---------------------------------------------------------------------------
# Validation + compression (shared by both backends)
# ---------------------------------------------------------------------------
def _process_upload(file: UploadFile) -> tuple[bytes, str]:
    """Validate an uploaded file and return (jpeg_bytes, unique_filename).

    Raises HTTPException(400) on anything that isn't a safe, real image.
    """
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "Only JPG, PNG or WEBP images are allowed.")

    data = file.file.read()
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > settings.MAX_IMAGE_MB * 1024 * 1024:
        raise HTTPException(400, f"Image must be under {settings.MAX_IMAGE_MB} MB.")

    # Confirm it's a genuine image, then re-open (verify() leaves it unusable).
    try:
        Image.open(io.BytesIO(data)).verify()
        img = Image.open(io.BytesIO(data))
    except Exception:
        raise HTTPException(400, "That file is not a valid image.")

    img = img.convert("RGB")
    img.thumbnail((1600, 1600))  # cap dimensions to keep pages fast
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=82, optimize=True)
    return buf.getvalue(), f"{uuid.uuid4().hex}.jpg"


# ---------------------------------------------------------------------------
# Supabase Storage REST helpers
# ---------------------------------------------------------------------------
def _sb_base() -> str:
    return settings.SUPABASE_URL.rstrip("/")


def _sb_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_KEY,
    }


def _sb_public_url(name: str) -> str:
    return f"{_sb_base()}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/{name}"


def _sb_upload(name: str, data: bytes) -> str:
    url = f"{_sb_base()}/storage/v1/object/{settings.SUPABASE_BUCKET}/{name}"
    try:
        resp = httpx.post(
            url, content=data, timeout=_HTTP_TIMEOUT,
            headers={**_sb_headers(), "Content-Type": "image/jpeg", "x-upsert": "true"},
        )
    except httpx.HTTPError as e:
        log.error("Supabase upload request failed: %s", e)
        raise HTTPException(502, "Could not reach image storage. Please try again.")
    if resp.status_code not in (200, 201):
        log.error("Supabase upload rejected (%s): %s", resp.status_code, resp.text[:300])
        raise HTTPException(502, "Image upload failed. Please try again.")
    return _sb_public_url(name)


def _sb_delete(name: str) -> None:
    url = f"{_sb_base()}/storage/v1/object/{settings.SUPABASE_BUCKET}/{name}"
    try:
        resp = httpx.request("DELETE", url, timeout=_HTTP_TIMEOUT, headers=_sb_headers())
        if resp.status_code not in (200, 404):
            log.warning("Supabase delete non-fatal (%s): %s", resp.status_code, resp.text[:200])
    except httpx.HTTPError as e:
        log.warning("Supabase delete request failed (ignored): %s", e)


# ---------------------------------------------------------------------------
# Public API (names kept stable so routers don't change)
# ---------------------------------------------------------------------------
def save_package_image(file: UploadFile) -> str:
    """Validate + store one image; return the reference to save in the DB.

    Returns a full Supabase public URL in production, or a "/uploads/..." path
    locally.
    """
    data, name = _process_upload(file)
    if settings.use_supabase_storage:
        return _sb_upload(name, data)
    # Local fallback
    path = os.path.join(LOCAL_DIR, name)
    with open(path, "wb") as f:
        f.write(data)
    return f"/uploads/packages/{name}"


def delete_image_file(ref: str) -> None:
    """Safely delete an image given whatever reference is stored in the DB.

    Handles both Supabase public URLs and local /uploads paths. Never raises —
    a storage hiccup must not block deleting or editing a package.
    """
    if not ref:
        return
    marker = f"/storage/v1/object/public/{settings.SUPABASE_BUCKET}/"
    try:
        if marker in ref:
            name = ref.split(marker, 1)[1]
            _sb_delete(name)
        elif ref.startswith("/uploads/"):
            local = ref.lstrip("/")
            if os.path.exists(local):
                os.remove(local)
    except Exception as e:  # defensive: deletion is best-effort
        log.warning("Image delete failed (ignored): %s", e)
