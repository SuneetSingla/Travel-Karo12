# Travel Karo — Production Architecture & Migration Plan

This documents the move from the original **SQLite + local image storage** setup
to a **production-ready** architecture, and how to run the migration.

## Final architecture

| Layer | Local development | Production |
|---|---|---|
| Backend | FastAPI + Jinja2 (unchanged) | same code |
| Database | SQLite file (`travelkaro.db`) | **Supabase PostgreSQL** (via pooler) |
| Image storage | local `uploads/` folder | **Supabase Storage** (public bucket) |
| Schema | **Alembic** (`alembic upgrade head`) | **Alembic** (run against the prod DB) |
| Admin auth | bcrypt + signed-cookie sessions | same (stateless; needs stable `SECRET_KEY`) |
| Hosting | `uvicorn` on localhost | **Vercel**, domain **travelkaro.net** (GoDaddy DNS) |

**Backend selection is automatic, by environment variables only** — no code
changes between environments:
- `DATABASE_URL` starting with `sqlite` → SQLite; `postgresql+psycopg://…` → Postgres.
- All three `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` / `SUPABASE_BUCKET` set → Supabase Storage; otherwise local disk.

## What changed (and what didn't)

**Changed**
- `app/config.py` — added `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_BUCKET`, plus `use_supabase_storage` / `is_sqlite` helpers.
- `app/database.py` — Postgres branch tuned for serverless + Supabase **transaction pooler**: `NullPool`, `pool_pre_ping=True`, and `prepare_threshold=None` (psycopg) to disable server-side prepared statements (required by the pgbouncer transaction pooler).
- `app/storage.py` (new) — image save/delete via Supabase Storage REST (httpx) with a local-disk fallback; secure validation, upload error handling, safe (non-throwing) deletion.
- `app/utils.py` — image functions moved to `storage.py` and re-exported (routers unchanged).
- `app/main.py` — **removed automatic schema creation at startup** (no `create_all`/ALTER on every cold start); default business-settings row is seeded by the initial migration and lazily on first read.
- `migrations/` + `alembic.ini` (new) — Alembic owns the schema; URL comes from settings, so one set of migrations serves SQLite and Postgres.
- `create_admin.py` — checks the schema exists (directs you to `alembic upgrade head`) instead of creating it.
- `.env.example` — documents Postgres + Supabase, with local/prod separation and secret-handling notes.

**Unchanged (preserved):** all templates, CSS/JS, routes, the admin panel, authentication, the CRM, analytics, and every piece of business logic. No files deleted.

## Security of secrets
- `SUPABASE_SERVICE_KEY` is used **only server-side** in `app/storage.py` (sent as an HTTP header to Supabase). It is never rendered into a template, never in a public image URL, and never sent to the browser.
- `.env` is git-ignored. In production the secrets live in **Vercel → Environment Variables**, not in the repo.

---

## Migration runbook

> Do this once, when moving existing local data to production. If you have no
> real data yet, just do steps 1–3 and 6 (create a fresh Postgres schema + admin).

### 1. Create the Supabase project
- New Supabase project → note the **database password**.
- **Database → Connect**: copy the **Transaction pooler** URI (port **6543**). Convert it to SQLAlchemy form:
  `postgresql+psycopg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require`
- **Storage → New bucket** → name `packages` → **Public bucket: ON**.
- **Project Settings → API**: copy the **service_role** key (secret).

### 2. Apply the schema to Postgres
```bash
DATABASE_URL="postgresql+psycopg://...:6543/postgres?sslmode=require" alembic upgrade head
```
Verify the connection + pooler compatibility:
```bash
DATABASE_URL="postgresql+psycopg://...:6543/postgres?sslmode=require" python scripts/check_db.py
```

### 3. Back up, then migrate the data (if you have existing SQLite data)
The script **backs up** your SQLite file first, then copies every table and
**re-syncs Postgres id sequences**:
```bash
DATABASE_URL="postgresql+psycopg://...:6543/postgres?sslmode=require" \
  python scripts/migrate_sqlite_to_postgres.py --source ./travelkaro.db
```
It prints source-vs-target row counts and foreign-key checks. Admin emails and
**bcrypt password hashes are copied verbatim**, so existing logins keep working.
Re-running is safe (idempotent — matches by primary key).

### 4. Migrate package images to Supabase Storage
```bash
SUPABASE_URL=... SUPABASE_SERVICE_KEY=... SUPABASE_BUCKET=packages \
DATABASE_URL="postgresql+psycopg://...:6543/postgres?sslmode=require" \
  python scripts/migrate_images_to_supabase.py
```
Uploads any local images, rewrites each package's image list to the Supabase
public URL, then HEAD-checks that the URLs are reachable. Idempotent.

### 5. Back up Postgres going forward
Supabase provides automated backups; you can also export via the dashboard or
`pg_dump`. (Your two data stores are now the Postgres DB and the Storage bucket.)

### 6. Deploy
See `DEPLOYMENT.md` for Vercel env vars and pointing the GoDaddy domain.

## Keeping local and production separate
- **Local** uses `.env` with the SQLite URL and no Supabase keys — it never
  touches the production database or bucket.
- **Production** config lives only in Vercel's environment variables.
- Don't put the production `DATABASE_URL` in your local `.env` for routine work;
  use it only transiently on the command line when running a migration script.
