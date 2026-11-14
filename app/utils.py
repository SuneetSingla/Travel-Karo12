"""Small helpers: spam limiting + text helpers.

Image storage lives in app/storage.py; the two image functions are re-exported
here so existing imports (``from ..utils import save_package_image`` etc.) keep
working unchanged.
"""
import time
from collections import defaultdict

# Re-export image storage API (backend chosen in storage.py).
from .storage import save_package_image, delete_image_file  # noqa: F401


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
