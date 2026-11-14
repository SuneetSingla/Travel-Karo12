# Travel Karo — Website + Admin Dashboard + CRM

A complete, working website for **Travel Karo** (Bathinda, Punjab), built with
**FastAPI + Jinja2 + SQLAlchemy**. One Python app runs everything.

**Architecture:** FastAPI backend · **SQLite + local images** for local dev ·
**Supabase PostgreSQL + Supabase Storage** in production · **Alembic** for
database migrations · deployed on **Vercel** behind the **travelkaro.net**
domain. The database and image backends are chosen purely by environment
variables (see `.env.example`), so the same code runs locally and in production.
Full details in `MIGRATION_PLAN.md` and `DEPLOYMENT.md`.

- **Public website** — Home, Destinations (Domestic / International tabs), About,
  Contact, a "Book Now" enquiry flow, a floating WhatsApp button, and IRCTC /
  GST trust labels.
- **Admin panel** (`/admin`, login required) — live dashboard with enquiry charts
  **and website-performance insights (page views + visitor clicks)**, package
  manager (image upload + Domestic/International category), a built-in CRM, and
  settings where the owner can change the **login email and password**.

> **Admin login:** the first account is created with `create_admin.py` (a
> temporary email + password). After logging in, change both under
> **Admin → Settings**. Auth uses secure signed-session cookies with bcrypt
> password hashing — no separate token setup needed.

Every enquiry from the website becomes a CRM lead **automatically** — no email,
no copy-paste. Packages you publish appear on the site instantly.

---

## ▶ Run it on your computer (localhost)

You need **Python 3.11+** installed. Then, from a terminal:

```bash
# 1. Go into the project folder
cd travel-karo

# 2. Create and activate a virtual environment
python -m venv .venv
#   macOS / Linux:
source .venv/bin/activate
#   Windows (PowerShell):
.venv\Scripts\Activate.ps1

# 3. Install the required packages
pip install -r requirements.txt

# 4. Create your settings file
#   macOS / Linux:
cp .env.example .env
#   Windows:
copy .env.example .env
#   Then open .env and set SECRET_KEY to a long random value.
#   Generate one with:
python -c "import secrets; print(secrets.token_hex(32))"

# 5. Create the database tables (schema is managed by Alembic)
alembic upgrade head

# 6. Create your admin login (asks for email + password)
python create_admin.py

# 7. Start the website
uvicorn app.main:app --reload
```

Now open your browser:

- **Website:**  http://localhost:8000
- **Admin:**    http://localhost:8000/admin  (log in with the email/password from step 6)

That's it. Locally, with no Supabase settings in `.env`, the app uses a **SQLite**
file (`travelkaro.db`) and saves uploaded images to the local `uploads/` folder —
no database or cloud account needed. Production uses Supabase Postgres + Storage
(see `DEPLOYMENT.md`); the switch is entirely via environment variables.

> **Schema changes** are applied with `alembic upgrade head` — the app never
> creates or alters tables on startup. After pulling changes that touch
> `app/models.py`, run `alembic upgrade head` again.

---

## 📁 What's inside

```
travel-karo/
├─ app/
│  ├─ main.py              App setup, static files, SEO, page-view tracking
│  ├─ config.py            Settings + absolute paths (reads from .env)
│  ├─ database.py          DB engine (SQLite locally / Postgres pooler in prod)
│  ├─ models.py            The 7 tables (admins, packages, enquiries, notes,
│  │                       settings, page_views, click_events)
│  ├─ auth.py              Password hashing (bcrypt) + login protection
│  ├─ storage.py           Image storage: Supabase Storage or local disk
│  ├─ utils.py             Spam limiter + text helpers
│  ├─ routers/             public.py (site + enquiry) · admin.py (admin + CRM)
│  ├─ templates/           All pages (Jinja2 HTML)
│  └─ static/              CSS, JavaScript, logo images
├─ migrations/             Alembic migrations (schema is applied explicitly)
├─ alembic.ini             Alembic config (DB URL comes from .env, not here)
├─ scripts/
│  ├─ migrate_sqlite_to_postgres.py   One-time SQLite → Postgres data migration
│  ├─ migrate_images_to_supabase.py   One-time local → Supabase image migration
│  └─ check_db.py                     Verify a live DB / Supabase pooler
├─ uploads/packages/       Local image folder (dev only)
├─ create_admin.py         Create / reset an admin login
├─ requirements.txt        Python packages
├─ .env.example            Settings template → copy to .env
├─ MIGRATION_PLAN.md       Final architecture + migration runbook
├─ DEPLOYMENT.md           Supabase + Vercel + GoDaddy deployment guide
└─ TESTING.md              What was tested and how to re-check
```

## 🎨 Changing the look & content

- **Brand colours (public site):** open `app/static/css/public.css` — the colours are
  at the very top under `:root`. The admin panel uses `app/static/css/styles.css`.
- **Logo:** replace `app/static/img/logo-wordmark.png` and `logo-emblem.jpg` with
  new files of the same name.
- **Business phone / email / address / socials:** change them in the **admin →
  Settings** page (no code needed) — they update across the website live.

## 🔒 Security built in
- Admin pages are blocked at the server for anyone who isn't logged in (not just
  hidden links).
- There is no public sign-up — admin accounts are created only via `create_admin.py`.
- Passwords are stored hashed (bcrypt), never in plain text.
- Customer enquiry data is only visible inside the admin panel.
- The public enquiry form has honeypot + rate-limit spam protection and
  server-side validation.

See **DEPLOYMENT.md** when you're ready to put it online and connect `travelkaro.net`.
