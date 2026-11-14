# Going live & connecting your GoDaddy domain (travelkaro.net)

This guide takes the site from your computer to the internet, on your own
domain. It assumes no server experience. Read it top to bottom.

> **Big picture:** GoDaddy sells you the *domain name* (travelkaro.net). The
> website itself has to *run somewhere* — on a small server. So there are two
> jobs: (1) put the app on a server, and (2) point your GoDaddy domain at that
> server. We do them in that order.

---

## Step 0 — Put the code on GitHub (recommended)

1. Create a free account at https://github.com and a new **private** repository
   called `travel-karo`.
2. In the project folder on your computer:
   ```bash
   git init
   git add .
   git commit -m "Travel Karo website"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/travel-karo.git
   git push -u origin main
   ```
   The `.gitignore` already keeps your secrets (`.env`), the database and
   uploaded photos out of GitHub.

---

## Step 1 — Get a server

I recommend a small **VPS** (virtual server) — about **₹350–500/month** — because
your app stores the database file and uploaded photos on disk, and a VPS keeps
them safely between restarts. Good options: **DigitalOcean**, **Hetzner**, or
**Linode**. Choose **Ubuntu 24.04**, the smallest plan.

After creating it you'll get a **server IP address** (e.g. `203.0.113.45`) and a
root password. Keep these.

> *Alternative (no server to manage):* **Render.com** can run the app, but its
> free disk resets on each deploy, so you'd also need its managed PostgreSQL and
> an image host. That's more moving parts. For simplicity, the VPS path below
> keeps everything in one place. If you prefer Render, tell me and I'll give you
> that variant (it mainly means setting `DATABASE_URL` to the Postgres one Render
> provides).

---

## Step 2 — Set up the server (one time)

Connect to it from your computer's terminal:
```bash
ssh root@YOUR-SERVER-IP
```
Then run these (copy–paste block by block):
```bash
apt update && apt upgrade -y
apt install -y python3-venv python3-pip nginx git
```
Get your code and install it:
```bash
cd /var/www
git clone https://github.com/YOUR-USERNAME/travel-karo.git
cd travel-karo
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```
Create the settings file:
```bash
cp .env.example .env
nano .env
```
In `.env` set:
- `SECRET_KEY=` → a long random value (run `python3 -c "import secrets; print(secrets.token_hex(32))"` and paste the result)
- `DATABASE_URL=sqlite:///./travelkaro.db`  (leave as is)
- `SITE_URL=https://www.travelkaro.net`
- `PRODUCTION=true`

Save (Ctrl+O, Enter, Ctrl+X). Create your admin login:
```bash
python create_admin.py
```

---

## Step 3 — Keep the app running (systemd)

Create a service so the app runs 24/7 and restarts automatically:
```bash
nano /etc/systemd/system/travelkaro.service
```
Paste:
```ini
[Unit]
Description=Travel Karo
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/travel-karo
ExecStart=/var/www/travel-karo/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
Start it:
```bash
systemctl daemon-reload
systemctl enable --now travelkaro
systemctl status travelkaro        # should say "active (running)"
```

---

## Step 4 — Put it on the web (nginx)

```bash
nano /etc/nginx/sites-available/travelkaro
```
Paste (note the `client_max_body_size` so photo uploads aren't blocked):
```nginx
server {
    listen 80;
    server_name travelkaro.net www.travelkaro.net;
    client_max_body_size 12M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Enable it:
```bash
ln -s /etc/nginx/sites-available/travelkaro /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx
```

---

## Step 5 — Point your GoDaddy domain at the server

1. Log in at **godaddy.com** → **My Products** → next to **travelkaro.net** click
   **DNS** (or "Manage DNS").
2. Under **Records**, set these two **A records** (edit the existing ones or add them):

   | Type | Name | Value (points to)   | TTL     |
   |------|------|---------------------|---------|
   | A    | `@`  | YOUR-SERVER-IP      | 1 hour  |
   | A    | `www`| YOUR-SERVER-IP      | 1 hour  |

   Remove any old "Parked" / forwarding record on `@` or `www` that points
   somewhere else.
3. Save. DNS changes can take anywhere from a few minutes to a couple of hours to
   spread. You can check progress at https://dnschecker.org (search `travelkaro.net`).

Once it resolves, http://travelkaro.net will show your site.

---

## Step 6 — Turn on HTTPS (the padlock) — free

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d travelkaro.net -d www.travelkaro.net
```
Answer the prompts (enter an email, agree, choose redirect to HTTPS). Certbot
auto-renews. Your site is now **https://www.travelkaro.net** 🎉

---

## Updating the site later

When you change the code (on GitHub):
```bash
ssh root@YOUR-SERVER-IP
cd /var/www/travel-karo
git pull
. .venv/bin/activate
pip install -r requirements.txt      # only if requirements changed
systemctl restart travelkaro
```

## Back up your data (important)

Your business data is two things on the server: `travelkaro.db` (packages +
enquiries) and the `uploads/` folder (photos). Copy them to your computer
regularly:
```bash
scp root@YOUR-SERVER-IP:/var/www/travel-karo/travelkaro.db ./backup-travelkaro.db
scp -r root@YOUR-SERVER-IP:/var/www/travel-karo/uploads ./backup-uploads
```

---

### If you only have GoDaddy shared/cPanel hosting (not a VPS)
GoDaddy's cPanel "Setup Python App" can run this, but it uses Passenger and needs
an extra ASGI shim, and photo storage/limits are fiddly. If that's your only
option, tell me your exact GoDaddy plan and I'll give you tailored steps — but a
small VPS (above) is the smoother, more reliable route.
