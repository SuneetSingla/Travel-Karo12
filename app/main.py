"""Travel Karo — FastAPI application entry point.

Run locally with:   uvicorn app.main:app --reload
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import settings, STATIC_DIR, UPLOADS_DIR
from .database import SessionLocal
from .templating import templates, base_context
from .routers import public, admin

# NOTE: The database schema is NOT created or migrated here. Schema changes are
# applied explicitly with Alembic ("alembic upgrade head"), so the app does no
# schema work at startup — important on serverless (Vercel), where startup runs
# on every cold start. See MIGRATION_PLAN.md. The default business-settings row
# is seeded lazily on first read (templating.get_business_settings).

app = FastAPI(title="Travel Karo")

# Signed-cookie sessions for admin login.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=settings.PRODUCTION,
    same_site="lax",
)

# Serve static assets and uploaded package images (absolute paths).
# check_dir=False lets the app boot even if the uploads folder doesn't exist yet
# (e.g. a fresh serverless instance).
try:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass  # read-only filesystem (serverless) — uploads need external storage
app.mount("/static", StaticFiles(directory=str(STATIC_DIR), check_dir=False), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR), check_dir=False), name="uploads")

app.include_router(public.router)
app.include_router(admin.router)


# --- Website visit tracking -------------------------------------------------
# Count one VISIT per browsing session, not one per page. A short-lived cookie
# marks an active visit; while it is set, navigating between pages does not add
# to the count. After ~30 minutes of inactivity the cookie expires and the next
# page view counts as a new visit. Admin, static files, uploads and the tracking
# endpoint are ignored.
_TRACKED_EXACT = {"/", "/packages", "/about", "/contact"}
_VISIT_COOKIE = "tk_v"
_VISIT_WINDOW = 1800  # seconds (30 minutes)


def _is_tracked(path: str) -> bool:
    if path in _TRACKED_EXACT:
        return True
    if path.startswith("/packages/") and path[len("/packages/"):].isdigit():
        return True
    return False


@app.middleware("http")
async def record_visit(request: Request, call_next):
    response = await call_next(request)
    try:
        if request.method == "GET" and response.status_code < 400 and _is_tracked(request.url.path):
            # Only the first page of a visit (no active cookie) counts.
            if not request.cookies.get(_VISIT_COOKIE):
                from .models import PageView
                db = SessionLocal()
                try:
                    db.add(PageView(path=request.url.path))
                    db.commit()
                finally:
                    db.close()
            # (Re)set the sliding visit cookie so later pages in this session
            # don't count again.
            response.set_cookie(
                _VISIT_COOKIE, "1", max_age=_VISIT_WINDOW,
                httponly=True, samesite="lax", secure=settings.PRODUCTION,
            )
    except Exception:
        pass  # analytics must never break a page load
    return response


# --- SEO: robots.txt and sitemap.xml ---------------------------------------
@app.get("/robots.txt", response_class=HTMLResponse)
def robots():
    body = f"User-agent: *\nAllow: /\nDisallow: /admin\nSitemap: {settings.SITE_URL}/sitemap.xml\n"
    return HTMLResponse(body, media_type="text/plain")


@app.get("/sitemap.xml", response_class=HTMLResponse)
def sitemap():
    pages = ["/", "/packages", "/contact"]
    urls = "".join(
        f"<url><loc>{settings.SITE_URL}{p}</loc></url>" for p in pages
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}</urlset>"
    )
    return HTMLResponse(xml, media_type="application/xml")


# Friendly 404 using the public layout.
@app.exception_handler(404)
async def not_found(request: Request, exc):
    ctx = base_context(request)
    ctx["message"] = "The page you were looking for doesn't exist."
    return templates.TemplateResponse("public/404.html", ctx, status_code=404)
