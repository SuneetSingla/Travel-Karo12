"""Admin authentication: password hashing + 'who is logged in' helpers."""
from fastapi import Request, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from .database import get_db
from .models import Admin

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> Admin | None:
    """Return the logged-in Admin, or None. Does not force a redirect."""
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return None
    return db.get(Admin, admin_id)


def require_admin(request: Request, db: Session = Depends(get_db)) -> Admin:
    """Dependency for protected admin pages. Redirects to login if not signed in.

    (A 303 with a Location header is how FastAPI issues a redirect from a
    dependency — the browser is sent to /admin/login.)
    """
    admin = get_current_admin(request, db)
    if admin is None:
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
    return admin
