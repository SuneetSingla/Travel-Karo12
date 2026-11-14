"""Database engine + session setup (SQLAlchemy 2.0).

Driven entirely by DATABASE_URL:
  • Local dev  -> sqlite:///./travelkaro.db   (zero setup)
  • Production -> postgresql+psycopg://...     (Supabase / Neon)

Serverless + Supabase notes (why the Postgres branch is configured as it is):
  • NullPool: on Vercel each invocation is short-lived, so we don't keep a
    connection pool across invocations — we open and close per request and let
    Supabase's connection pooler do the pooling.
  • prepare_threshold=None: Supabase's TRANSACTION pooler (pgbouncer, port 6543)
    does not support server-side prepared statements. psycopg(3) uses them by
    default, which would raise "prepared statement already exists". Setting the
    threshold to None disables implicit prepared statements, making the app
    compatible with the transaction pooler. (The session pooler on 5432 works
    too; this setting is safe for both.)
  • pool_pre_ping: drops dead connections before using them.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import settings

if settings.is_sqlite:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    # PostgreSQL via psycopg(3). Compatible with Supabase transaction pooler.
    engine = create_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: one database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
