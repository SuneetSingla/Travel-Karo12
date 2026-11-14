"""Verify the live database connection — especially Supabase pooler compatibility.

Run this with your production DATABASE_URL to confirm the app can connect and
that prepared-statement handling works through the Supabase transaction pooler:

    DATABASE_URL="postgresql+psycopg://...:6543/postgres?sslmode=require" \
        python scripts/check_db.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.pool import NullPool
from app.config import settings
from app.database import engine


def main() -> None:
    print(f"Dialect     : {engine.dialect.name}")
    print(f"NullPool    : {isinstance(engine.pool, NullPool)}")
    if settings.is_sqlite:
        print("Using SQLite (local) — pooler checks not applicable.")

    # 1. Basic connectivity.
    with engine.connect() as c:
        print("SELECT 1    :", c.execute(text("SELECT 1")).scalar())
        if not settings.is_sqlite:
            print("Server      :", c.execute(text("SHOW server_version")).scalar())

    # 2. Exercise the prepared-statement path across several fresh connections,
    #    which is where the transaction pooler would fail if prepared statements
    #    were enabled ("prepared statement already exists").
    for i in range(3):
        with engine.connect() as c:
            c.execute(text("SELECT :n + :m"), {"n": i, "m": 1}).scalar()
    print("Param query x3: OK (no prepared-statement conflict)")

    # 3. Confirm the schema has been applied (alembic upgrade head).
    with engine.connect() as c:
        try:
            ver = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
            print("Alembic ver :", ver)
        except Exception:
            print("Alembic ver : (alembic_version table not found — run 'alembic upgrade head')")

    print("\n✅ Database connection OK.")


if __name__ == "__main__":
    main()
