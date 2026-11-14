"""Jinja2 template engine + values made available to every template."""
from datetime import datetime

from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from .config import settings, TEMPLATES_DIR
from .database import SessionLocal
from .models import BusinessSettings, SERVICES, LEAD_STATUSES
from .utils import lines_to_list

# Absolute path — resolves from any working directory (local, VPS or serverless).
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Handy helpers usable inside templates
templates.env.filters["as_list"] = lines_to_list


_DEFAULT_SETTINGS = dict(
    phone="+91 98142-54414",
    email="info@travelkaro.net",
    address="#4910, Post Office Bazar, Bathinda, Punjab – 151005, India",
    website="www.travelkaro.net",
    instagram="https://instagram.com/travelkaro12",
    facebook="https://facebook.com/travelkaro12",
)


def get_business_settings() -> BusinessSettings:
    """Fetch the single business-settings row (used in footer/contact everywhere).

    Seeds the default row lazily on first access (not at startup, so the app does
    no DB work on a serverless cold start). If the DB is unavailable or read-only,
    returns an in-memory default so templates never crash.
    """
    db = SessionLocal()
    try:
        row = db.get(BusinessSettings, 1)
        if row is None:
            row = BusinessSettings(id=1, **_DEFAULT_SETTINGS)
            db.add(row)
            db.commit()
            db.refresh(row)
        return row
    except Exception:
        db.rollback()
        return BusinessSettings(id=1, **_DEFAULT_SETTINGS)  # transient fallback
    finally:
        db.close()


# Global values injected into every render via templates.TemplateResponse(context=...)
def base_context(request) -> dict:
    return {
        "request": request,
        "brand_name": settings.BRAND_NAME,
        "tagline": settings.BRAND_TAGLINE,
        "services": SERVICES,
        "lead_statuses": LEAD_STATUSES,
        "biz": get_business_settings(),
        "year": datetime.now().year,
        "site_url": settings.SITE_URL,
    }
