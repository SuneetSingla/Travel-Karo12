# Travel Karo — Website + Admin Dashboard + CRM

A complete, working website for **Travel Karo** (Bathinda, Punjab), built with
**FastAPI + Jinja2 + SQLAlchemy**. One Python app runs everything:

- **Public website** — Home, Packages (+ detail pages), Contact Us, and a
  "Book a Package" enquiry flow.
- **Admin panel** (`/admin`, login required) — live dashboard with charts,
  package manager (with image upload), a built-in CRM, and settings.

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

# 5. Create your admin login (asks for email + password)
python create_admin.py

# 6. Start the website
uvicorn app.main:app --reload
```

Now open your browser:

- **Website:**  http://localhost:8000
- **Admin:**    http://localhost:8000/admin  (log in with the email/password from step 5)

That's it. On first run it creates a `travelkaro.db` SQLite file automatically —
no database to install. Uploaded package images are saved in the `uploads/` folder.

---

## 📁 What's inside

```
travel-karo/
├─ app/
│  ├─ main.py              App setup, static files, SEO (robots, sitemap)
│  ├─ config.py            Settings (reads from .env)
│  ├─ database.py          Database connection (SQLite locally / Postgres in prod)
│  ├─ models.py            The 5 tables (packages, enquiries, notes, settings, admins)
│  ├─ auth.py              Password hashing + login protection
│  ├─ utils.py             Image upload, spam limiter, helpers
│  ├─ routers/
│  │  ├─ public.py         Home, Packages, Contact, enquiry submission
│  │  └─ admin.py          Login, dashboard, packages, CRM, settings
│  ├─ templates/           All pages (Jinja2 HTML)
│  └─ static/              CSS, JavaScript, logo images
├─ uploads/packages/       Uploaded package photos (created automatically)
├─ create_admin.py         Create / reset an admin login
├─ requirements.txt        Python packages
├─ .env.example            Settings template → copy to .env
├─ DEPLOYMENT.md           How to go live + connect your GoDaddy domain
└─ TESTING.md              What was tested and how to re-check
```

## 🎨 Changing the look & content

- **Brand colours:** open `app/static/css/styles.css` — the colours are at the very
  top under `:root`. Change them in one place and the whole site updates.
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
