"""Upload existing local package images to Supabase Storage (idempotent).

For every package, any image still stored as a local "/uploads/packages/..."
path is uploaded to Supabase and the package's images list is rewritten to the
Supabase public URL. Images that are already Supabase URLs are left untouched,
so the script is safe to run multiple times.

Run AFTER the database migration, with the Supabase env vars set and
DATABASE_URL pointing at the database that holds the records:

    SUPABASE_URL=... SUPABASE_SERVICE_KEY=... SUPABASE_BUCKET=packages \
    DATABASE_URL="postgresql+psycopg://...:6543/postgres?sslmode=require" \
        python scripts/migrate_images_to_supabase.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import engine
from app.models import Package
from app import storage


def main() -> None:
    if not settings.use_supabase_storage:
        sys.exit("Supabase env vars not set. Set SUPABASE_URL / SUPABASE_SERVICE_KEY / SUPABASE_BUCKET.")

    Session = sessionmaker(bind=engine)
    db = Session()
    marker = f"/storage/v1/object/public/{settings.SUPABASE_BUCKET}/"

    scanned = migrated = skipped = missing = reachable = 0
    try:
        for pkg in db.query(Package).all():
            images = list(pkg.images or [])
            new_images = []
            changed = False
            for ref in images:
                scanned += 1
                if marker in ref:
                    skipped += 1
                    new_images.append(ref)
                    continue
                if ref.startswith("/uploads/"):
                    local = ref.lstrip("/")
                    if not os.path.exists(local):
                        print(f"  ! missing local file, left as-is: {ref}")
                        missing += 1
                        new_images.append(ref)
                        continue
                    with open(local, "rb") as f:
                        data = f.read()
                    name = os.path.basename(local)
                    public_url = storage._sb_upload(name, data)  # uploads + returns URL
                    new_images.append(public_url)
                    migrated += 1
                    changed = True
                else:
                    new_images.append(ref)
            if changed:
                pkg.images = new_images
                db.add(pkg)
                db.commit()
                print(f"  ✓ package #{pkg.id} '{pkg.title}' -> {len([i for i in new_images if marker in i])} Supabase image(s)")
    finally:
        db.close()

    # Verify the migrated URLs are actually reachable.
    print("\n=== Verifying uploaded URLs ===")
    db = Session()
    try:
        for pkg in db.query(Package).all():
            for ref in (pkg.images or []):
                if marker in ref:
                    try:
                        r = httpx.head(ref, timeout=15.0, follow_redirects=True)
                        if r.status_code == 200:
                            reachable += 1
                        else:
                            print(f"  ! not reachable ({r.status_code}): {ref}")
                    except httpx.HTTPError as e:
                        print(f"  ! check failed: {ref} ({e})")
    finally:
        db.close()

    print("\n=== Summary ===")
    print(f"images scanned : {scanned}")
    print(f"migrated       : {migrated}")
    print(f"already on cloud: {skipped}")
    print(f"missing local  : {missing}")
    print(f"reachable (200): {reachable}")
    print("\n✅ Image migration complete." if missing == 0 else
          "\n⚠️  Some local files were missing — review above.")


if __name__ == "__main__":
    main()
