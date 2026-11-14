"""Migrate TravelKaro data from SQLite to PostgreSQL (idempotent).

What it does, safely:
  1. Backs up the source SQLite file first.
  2. Copies every table (admins, business_settings, packages, enquiries,
     enquiry_notes, page_views, click_events) preserving primary keys, foreign
     keys and bcrypt password hashes.
  3. Re-synchronises PostgreSQL id sequences so new inserts don't collide.
  4. Verifies row counts and foreign-key integrity, and prints a report.

Idempotent: re-running updates existing rows in place (match by primary key)
rather than duplicating them.

The TARGET schema must already exist — create it first with:
    DATABASE_URL="postgresql+psycopg://...:6543/postgres?sslmode=require" alembic upgrade head

Usage:
    DATABASE_URL="postgresql+psycopg://...:6543/postgres?sslmode=require" \
        python scripts/migrate_sqlite_to_postgres.py --source ./travelkaro.db

(--target may be given instead of relying on DATABASE_URL.)
"""
import argparse
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select, func, inspect
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Admin, BusinessSettings, Package, Enquiry, EnquiryNote, PageView, ClickEvent

# FK-safe order: parents before children.
MODELS = [Admin, BusinessSettings, Package, Enquiry, EnquiryNote, PageView, ClickEvent]


def backup_sqlite(path: str) -> None:
    if path.startswith("sqlite"):
        # path given as a URL; extract file
        path = path.split("///")[-1]
    if os.path.exists(path):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = f"{path}.backup-{stamp}"
        shutil.copy2(path, dest)
        print(f"✓ Backup created: {dest}")
    else:
        print(f"! Source file {path} not found (nothing to back up).")


def copy_table(model, src_session, tgt_conn) -> int:
    table = model.__table__
    pk = list(table.primary_key.columns)[0]
    rows = src_session.query(model).all()
    for obj in rows:
        values = {c.name: getattr(obj, c.name) for c in table.columns}
        pk_val = values[pk.name]
        exists = tgt_conn.execute(select(pk).where(pk == pk_val)).first()
        if exists:
            non_pk = {k: v for k, v in values.items() if k != pk.name}
            if non_pk:
                tgt_conn.execute(table.update().where(pk == pk_val).values(**non_pk))
        else:
            tgt_conn.execute(table.insert().values(**values))
    return len(rows)


def sync_sequences(tgt_conn, dialect: str) -> None:
    if dialect != "postgresql":
        print("• Sequence sync skipped (target is not PostgreSQL).")
        return
    from sqlalchemy import text
    for model in MODELS:
        tname = model.__tablename__
        # setval to MAX(id); is_called=false when table is empty so next id = 1.
        tgt_conn.execute(text(f"""
            SELECT setval(
                pg_get_serial_sequence('{tname}', 'id'),
                COALESCE((SELECT MAX(id) FROM {tname}), 1),
                (SELECT COUNT(*) FROM {tname}) > 0
            )
        """))
    print("✓ PostgreSQL id sequences synchronised.")


def verify(src_session, tgt_conn) -> bool:
    ok = True
    print("\n=== Verification ===")
    print(f"{'table':<20}{'source':>10}{'target':>10}")
    for model in MODELS:
        s = src_session.query(func.count()).select_from(model).scalar()
        t = tgt_conn.execute(select(func.count()).select_from(model.__table__)).scalar()
        flag = "" if s == t else "  <-- MISMATCH"
        if s != t:
            ok = False
        print(f"{model.__tablename__:<20}{s:>10}{t:>10}{flag}")

    # Foreign-key integrity on the target.
    orphan_notes = tgt_conn.execute(select(func.count()).select_from(EnquiryNote.__table__)
        .where(EnquiryNote.enquiry_id.notin_(select(Enquiry.id)))).scalar()
    orphan_pkg = tgt_conn.execute(select(func.count()).select_from(Enquiry.__table__)
        .where(Enquiry.package_id.is_not(None))
        .where(Enquiry.package_id.notin_(select(Package.id)))).scalar()
    print(f"\nFK check — notes with missing enquiry: {orphan_notes}")
    print(f"FK check — enquiries with missing package: {orphan_pkg}")
    if orphan_notes or orphan_pkg:
        ok = False
    return ok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="./travelkaro.db", help="Source SQLite file")
    ap.add_argument("--target", default=os.environ.get("DATABASE_URL", ""),
                    help="Target DB URL (defaults to DATABASE_URL)")
    args = ap.parse_args()

    if not args.target:
        sys.exit("No target DB. Set DATABASE_URL or pass --target.")
    if not os.path.exists(args.source):
        sys.exit(f"Source SQLite file not found: {args.source}")

    print(f"Source: {args.source}\nTarget: {args.target.split('@')[-1]}\n")
    backup_sqlite(args.source)

    src_engine = create_engine(f"sqlite:///{args.source}", connect_args={"check_same_thread": False})
    tgt_engine = create_engine(args.target)
    dialect = tgt_engine.dialect.name

    # Target schema must exist (created by Alembic).
    if "admins" not in inspect(tgt_engine).get_table_names():
        sys.exit("Target schema not found. Run 'alembic upgrade head' against the target first.")

    SrcSession = sessionmaker(bind=src_engine)
    src_session = SrcSession()

    print("\n=== Copying tables ===")
    with tgt_engine.begin() as tgt_conn:
        for model in MODELS:
            n = copy_table(model, src_session, tgt_conn)
            print(f"  {model.__tablename__:<20} {n} row(s)")
        sync_sequences(tgt_conn, dialect)

    with tgt_engine.connect() as tgt_conn:
        ok = verify(src_session, tgt_conn)

    src_session.close()
    print("\n" + ("✅ Migration verified — counts and foreign keys match."
                  if ok else "⚠️  Verification found mismatches — review above."))
    print("Next: migrate images with scripts/migrate_images_to_supabase.py")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
