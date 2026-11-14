"""End-to-end test for the Travel Karo app.

Uses a temporary throwaway database so it never touches your real data.
Run with:  PYTHONPATH=. python tests/test_app.py
(Needs the test-only package httpx:  pip install httpx)
"""
import os
import tempfile

# Point the app at a temporary database BEFORE importing it.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["SECRET_KEY"] = "test-secret"

import io
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Admin, Enquiry, Package, PageView, ClickEvent
from app.auth import hash_password

# Seed a known admin.
db = SessionLocal()
db.query(Admin).delete(); db.commit()
db.add(Admin(email="test@travelkaro.net", password_hash=hash_password("password123")))
db.commit(); db.close()

c = TestClient(app, follow_redirects=False)
passed = 0


def ok(label, cond):
    global passed
    print(("PASS " if cond else "FAIL ") + label)
    assert cond, label
    passed += 1


ok("home loads", c.get("/").status_code == 200)
ok("packages loads", c.get("/packages").status_code == 200)
ok("contact loads", c.get("/contact").status_code == 200)
ok("about loads", c.get("/about").status_code == 200)
ok("page view recorded", SessionLocal().query(PageView).count() > 0)
ok("robots disallows admin", "Disallow: /admin" in c.get("/robots.txt").text)
ok("sitemap generated", "<urlset" in c.get("/sitemap.xml").text)

ok("admin blocked logged out", c.get("/admin").status_code == 303)
ok("admin packages blocked", c.get("/admin/packages").status_code == 303)
ok("admin enquiries blocked", c.get("/admin/enquiries").status_code == 303)

n0 = SessionLocal().query(Enquiry).count()
r = c.post("/enquiry", data={"customer_name": "Ramesh K", "phone": "9876500000",
                             "interested_service": "Air Tickets", "message": "Delhi-Dubai"})
ok("enquiry submit redirects", r.status_code == 303)
dbx = SessionLocal(); lead = dbx.query(Enquiry).order_by(Enquiry.id.desc()).first()
ok("CRM lead created", dbx.query(Enquiry).count() == n0 + 1)
ok("source = Service Enquiry", lead.source == "Service Enquiry")
dbx.close()

n1 = SessionLocal().query(Enquiry).count()
c.post("/enquiry", data={"customer_name": "Bot", "phone": "111", "company": "spamco"})
ok("honeypot blocks bot", SessionLocal().query(Enquiry).count() == n1)

ok("bad login rejected", c.post("/admin/login", data={"email": "test@travelkaro.net", "password": "x"}).status_code == 401)
ok("good login", c.post("/admin/login", data={"email": "test@travelkaro.net", "password": "password123"}).status_code == 303)
ok("dashboard after login", c.get("/admin").status_code == 200)
ok("enquiries list after login", c.get("/admin/enquiries").status_code == 200)

img = io.BytesIO(); Image.new("RGB", (800, 500), (90, 50, 154)).save(img, "PNG"); img.seek(0)
r = c.post("/admin/packages/save",
           data={"title": "Magical Bali", "destination": "Bali", "duration": "5N/6D",
                 "starting_price": "45000", "short_description": "Beaches",
                 "category": "international", "status": "published"},
           files={"images": ("bali.png", img, "image/png")})
ok("package saved", r.status_code == 303)
p = SessionLocal(); pkg = p.query(Package).order_by(Package.id.desc()).first(); pid = pkg.id
ok("package has image", len(pkg.images) == 1)
ok("package category saved", pkg.category == "international")
ok("package published", pkg.status == "published"); p.close()

ok("published pkg public", "Magical Bali" in c.get("/packages").text)
ok("pkg detail loads", c.get(f"/packages/{pid}").status_code == 200)
c.post(f"/admin/packages/{pid}/status", data={"to": "draft"})
ok("unpublished hidden", "Magical Bali" not in c.get("/packages").text)
ok("unpublished detail 404", c.get(f"/packages/{pid}").status_code == 404)

c.post(f"/admin/packages/{pid}/status", data={"to": "published"})
c.post("/enquiry", data={"customer_name": "Booker", "phone": "9000000001", "package_id": str(pid)})
bl = SessionLocal().query(Enquiry).order_by(Enquiry.id.desc()).first()
ok("booking lead linked", bl.package_id == pid and bl.source == "Package Booking")

c.post(f"/admin/enquiries/{lead.id}/note", data={"note": "Called, sending quote"})
c.post(f"/admin/enquiries/{lead.id}/update", data={"status": "Quotation Sent", "follow_up_date": "2026-12-01"})
L = SessionLocal().get(Enquiry, lead.id)
ok("note added", len(L.notes) == 1)
ok("status updated", L.status == "Quotation Sent")

c.post(f"/admin/packages/{pid}/delete")
g = SessionLocal()
ok("package deleted", g.get(Package, pid) is None)
ok("booking lead survives delete", g.query(Enquiry).filter(Enquiry.customer_name == "Booker").first() is not None)
g.close()

# 12. click tracking records an event
n_clicks = SessionLocal().query(ClickEvent).count()
c.post("/track", json={"kind": "whatsapp", "label": "test"})
ok("click event tracked", SessionLocal().query(ClickEvent).count() == n_clicks + 1)
c.post("/track", json={"kind": "not_a_real_kind"})
ok("invalid click kind ignored", SessionLocal().query(ClickEvent).count() == n_clicks + 1)

# 13. admin can change login email
r = c.post("/admin/settings/email", data={"new_email": "owner@travelkaro.net", "current_password": "password123"})
ok("email change redirects ok", "eml=ok" in r.headers.get("location", ""))
ok("email updated", SessionLocal().query(Admin).filter(Admin.email == "owner@travelkaro.net").first() is not None)
r = c.post("/admin/settings/email", data={"new_email": "x@y.com", "current_password": "WRONG"})
ok("email change needs correct password", "eml=wrong" in r.headers.get("location", ""))

# 14. dashboard renders with analytics present
ok("dashboard renders with analytics", c.get("/admin").status_code == 200)

os.unlink(_tmp.name)
print(f"\n{passed} checks passed ✅")
