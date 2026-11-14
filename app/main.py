"""Travel Karo — FastAPI application entry point.

Run locally with:   uvicorn app.main:app --reload
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .database import Base, engine, SessionLocal
from .models import BusinessSettings
from .templating import templates, base_context
from .routers import public, admin

# Create tables on first run (safe to call every start).
Base.metadata.create_all(bind=engine)


def ensure_business_settings_row() -> None:
    """Make sure the single editable business-info row exists with defaults."""
    db = SessionLocal()
    try:
        if db.get(BusinessSettings, 1) is None:
            db.add(BusinessSettings(
                id=1,
                phone="+91 98142-54414",
                email="info@travelkaro.net",
                address="#4910, Post Office Bazar, Bathinda, Punjab – 151005, India",
                website="www.travelkaro.net",
                instagram="https://instagram.com/travelkaro12",
                facebook="https://facebook.com/travelkaro12",
            ))
            db.commit()
    finally:
        db.close()


ensure_business_settings_row()

app = FastAPI(title="Travel Karo")

# Signed-cookie sessions for admin login.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=settings.PRODUCTION,
    same_site="lax",
)

# Serve static assets and uploaded package images.
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(public.router)
app.include_router(admin.router)


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
