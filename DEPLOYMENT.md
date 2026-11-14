# Deploying Travel Karo (Supabase + Vercel + GoDaddy)

Production architecture: **FastAPI on Vercel**, **Supabase PostgreSQL** (data),
**Supabase Storage** (images), **travelkaro.net** via GoDaddy DNS.

Read `MIGRATION_PLAN.md` for the one-time data/image migration. This guide is the
deployment itself. Do the steps in order.

---

## 1. Supabase (database + image storage)

1. Create a project at https://supabase.com — save the **database password**.
2. **Storage → New bucket** → name it `packages` → turn **Public bucket ON** → create.
3. **Project Settings → API** → copy the **`service_role`** key (this is secret).
4. **Database → Connect** → copy the **Transaction pooler** connection string
   (host ends in `pooler.supabase.com`, port **6543**). Rewrite it for SQLAlchemy:
   ```
   postgresql+psycopg://postgres.<ref>:<DB-PASSWORD>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require
   ```

## 2. Create the schema + first admin (from your computer, once)

With the Postgres URL from step 1:
```bash
# create the tables in Postgres
DATABASE_URL="postgresql+psycopg://...:6543/postgres?sslmode=require" alembic upgrade head

# confirm connectivity + pooler compatibility
DATABASE_URL="postgresql+psycopg://...:6543/postgres?sslmode=require" python scripts/check_db.py

# create the admin login in Postgres
DATABASE_URL="postgresql+psycopg://...:6543/postgres?sslmode=require" python create_admin.py
```
(If you have existing local data/images, run the two migration scripts now — see
`MIGRATION_PLAN.md` steps 3–4.)

## 3. Push to GitHub
Already done — the repo is `SuneetSingla/Travel-Karo12`, branch `main`. Vercel
deploys from it.

## 4. Vercel

1. https://vercel.com → **Add New → Project** → import `Travel-Karo12`.
2. Framework preset: **Other** (the included `vercel.json` handles the Python build
   and ships the templates/static files).
3. **Environment Variables** (Settings → Environment Variables) — add:
   | Name | Value |
   |---|---|
   | `SECRET_KEY` | a long random string (`python -c "import secrets;print(secrets.token_hex(32))"`) |
   | `DATABASE_URL` | the Postgres **pooler** URL from step 1 |
   | `SUPABASE_URL` | `https://<ref>.supabase.co` |
   | `SUPABASE_SERVICE_KEY` | the `service_role` key (secret) |
   | `SUPABASE_BUCKET` | `packages` |
   | `SITE_URL` | `https://www.travelkaro.net` |
   | `PRODUCTION` | `true` |
4. **Deploy.** When it finishes, open the `*.vercel.app` URL — the site should load,
   `/admin` should let you log in, and adding a package should upload the image to
   Supabase and persist across reloads.

> Keep `SECRET_KEY` stable — changing it later logs everyone out (sessions are
> signed with it). Never commit any of these values; they live only in Vercel.

## 5. Connect the GoDaddy domain

1. Vercel → Project → **Settings → Domains** → add `travelkaro.net` and `www.travelkaro.net`.
   Vercel shows the exact DNS records to create.
2. In **GoDaddy → My Products → travelkaro.net → DNS**, set what Vercel asked for — typically:
   | Type | Name | Value |
   |---|---|---|
   | A | `@` | `76.76.21.21` (use the IP Vercel shows) |
   | CNAME | `www` | `cname.vercel-dns.com` (use the value Vercel shows) |
   Remove any old parked/forwarding records on `@`/`www`.
3. Back in Vercel, wait for the domain to verify (minutes to a couple of hours).
   HTTPS is issued automatically. Site is live at **https://www.travelkaro.net**.

## 6. Updating later
Push to `main` → Vercel redeploys automatically. If a change alters
`app/models.py`, run `alembic upgrade head` against the production `DATABASE_URL`
once (from your computer) — Vercel does **not** run migrations itself, by design.

---

### Notes on why this works on serverless
- The app does **no schema work at startup** (Alembic owns migrations), so cold
  starts are clean and safe.
- No local disk is used in production: data is in Postgres, images in Supabase
  Storage — so Vercel's read-only filesystem is a non-issue.
- The Postgres engine is configured for the Supabase **transaction pooler**
  (`NullPool`, prepared statements disabled), avoiding pooler errors.

### Alternative host (VPS)
If you ever prefer a single server instead of Vercel, the app also runs under
`uvicorn` behind nginx with the same Postgres + Supabase settings. Ask and I'll
provide those steps — but Vercel + Supabase above is the recommended path.
