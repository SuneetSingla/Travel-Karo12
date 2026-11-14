# Testing

An automated end-to-end test (`tests/test_app.py`) verifies the whole app against
the project's requirements. Run it any time:

```bash
. .venv/bin/activate
pip install httpx          # test-only dependency
PYTHONPATH=. python tests/test_app.py
```

It uses a temporary throwaway database and checks all of the following — every
item passed when this project was delivered:

| # | Requirement | Result |
|---|-------------|--------|
| 1 | Home, Packages, Contact pages load | ✅ |
| 2 | robots.txt disallows /admin; sitemap.xml generated | ✅ |
| 3 | Admin pages are blocked for logged-out visitors (redirect to login) | ✅ |
| 4 | Contact-form submission creates a CRM lead automatically | ✅ |
| 5 | Lead source is detected correctly (Contact / Service / Package) | ✅ |
| 6 | Honeypot silently blocks bot submissions | ✅ |
| 7 | Wrong password rejected; correct password logs in | ✅ |
| 8 | Admin dashboard & enquiries list load after login | ✅ |
| 9 | Admin can add a package with an uploaded image | ✅ |
| 10 | Publishing a package makes it visible on the public site | ✅ |
| 11 | Unpublishing hides it from the public site (detail → 404) | ✅ |
| 12 | "Book This Package" enquiry links the lead to the package | ✅ |
| 13 | Admin can add internal notes to a lead | ✅ |
| 14 | Admin can change a lead's status and set a follow-up date | ✅ |
| 15 | Deleting a package keeps its past booking leads intact | ✅ |

Mobile responsiveness is handled in CSS with breakpoints for a collapsible nav
and a slide-in admin sidebar.

## Production-architecture verification (Supabase/Postgres migration)

These were verified during the migration work:

| Area | Verified |
|---|---|
| Alembic migration applies on SQLite (tables + seed row + version stamp) | ✅ |
| Alembic renders valid **PostgreSQL** DDL offline (`alembic upgrade head --sql`) | ✅ |
| Postgres engine uses `NullPool` + disabled prepared statements (pooler-safe) | ✅ |
| App runs on an **Alembic-built** schema (no `create_all` at startup) — 15 end-to-end checks | ✅ |
| Supabase Storage upload returns a public URL; service key stays in the header only | ✅ |
| Image delete parses Supabase URL / local path correctly; validation rejects non-images | ✅ |
| `migrate_sqlite_to_postgres.py`: counts match, FKs intact, bcrypt hashes preserved, **idempotent** | ✅ |
| `migrate_images_to_supabase.py`: migrates local, skips cloud, flags missing, **idempotent** | ✅ |

**Not testable in this environment (needs your live Supabase):** the actual
network connection to the Supabase transaction pooler. Verify it with your real
credentials using `python scripts/check_db.py` (it runs connectivity + a
repeated parameterised query to confirm no prepared-statement conflict).
