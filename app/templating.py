"""Jinja2 template engine + values made available to every template."""
from datetime import datetime

from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from .config import settings
from .database import SessionLocal
from .models import BusinessSettings, SERVICES, LEAD_STATUSES
from .utils import lines_to_list

templates = Jinja2Templates(directory="app/templates")

# Handy helpers usable inside templates
templates.env.filters["as_list"] = lines_to_list


def get_business_settings() -> BusinessSettings:
    """Fetch the single business-settings row (used in footer/contact everywhere)."""
    db = SessionLocal()
    try:
        row = db.get(BusinessSettings, 1)
        return row
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
