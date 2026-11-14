"""Central settings, loaded from the .env file."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute paths anchored to this file's location, so templates, static files
# and uploads resolve no matter what the process's working directory is.
# (On serverless hosts like Vercel the working directory is NOT the repo root,
# which is why relative paths such as "app/templates" fail there.)
APP_DIR = Path(__file__).resolve().parent          # .../app
PROJECT_ROOT = APP_DIR.parent                      # repo root
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
UPLOADS_DIR = PROJECT_ROOT / "uploads"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: str = "dev-insecure-secret-change-me"
    DATABASE_URL: str = "sqlite:///./travelkaro.db"
    SITE_URL: str = "http://localhost:8000"
    PRODUCTION: bool = False

    # Fixed brand details (used across the site). Contact info that the admin
    # can change lives in the database (business_settings), not here.
    BRAND_NAME: str = "Travel Karo"
    BRAND_TAGLINE: str = "Let's Make Memories."

    # Image upload limits
    MAX_IMAGE_MB: int = 5
    ALLOWED_IMAGE_TYPES: tuple = ("image/jpeg", "image/png", "image/webp")


settings = Settings()
