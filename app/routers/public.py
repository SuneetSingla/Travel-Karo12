"""Public website routes: Home, Packages, Package detail, Contact + enquiry submit."""
from datetime import datetime, date

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Package, Enquiry, SERVICES, ENQUIRY_SOURCES
from ..templating import templates, base_context
from ..utils import too_many_submissions

router = APIRouter()


def published_packages(db: Session, limit: int | None = None):
    stmt = (
        select(Package)
        .where(Package.status == "published")
        .order_by(Package.created_at.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    return db.scalars(stmt).all()


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    ctx = base_context(request)
    ctx["featured"] = published_packages(db, limit=6)
    ctx["page_title"] = "Travel Karo — Holidays, Flights, Visas & More | Bathinda"
    ctx["meta_description"] = (
        "Travel Karo is a family-owned travel agency in Bathinda offering holiday "
        "packages, air tickets, hotels, visas, cruises and travel insurance. "
        "Let's make memories."
    )
    return templates.TemplateResponse("public/home.html", ctx)


@router.get("/packages")
def packages(request: Request, db: Session = Depends(get_db)):
    ctx = base_context(request)
    ctx["packages"] = published_packages(db)
    ctx["page_title"] = "Holiday Packages | Travel Karo"
    ctx["meta_description"] = (
        "Explore holiday packages from Travel Karo — thoughtfully planned trips with "
        "seamless bookings and personalised assistance."
    )
    return templates.TemplateResponse("public/packages.html", ctx)


@router.get("/packages/{package_id}")
def package_detail(package_id: int, request: Request, db: Session = Depends(get_db)):
    pkg = db.get(Package, package_id)
    if pkg is None or pkg.status != "published":
        ctx = base_context(request)
        ctx["message"] = "This package is not available."
        return templates.TemplateResponse("public/404.html", ctx, status_code=404)
    ctx = base_context(request)
    ctx["pkg"] = pkg
    ctx["page_title"] = f"{pkg.title} | Travel Karo"
    ctx["meta_description"] = (pkg.short_description or "")[:160]
    return templates.TemplateResponse("public/package_detail.html", ctx)


@router.get("/contact")
def contact(
    request: Request,
    db: Session = Depends(get_db),
    service: str | None = None,
    package: int | None = None,
    sent: int | None = None,
):
    """Contact page. Pre-fills the service or the selected package from the query."""
    ctx = base_context(request)
    selected_package = db.get(Package, package) if package else None
    ctx.update(
        prefill_service=service if service in SERVICES else None,
        selected_package=selected_package if (selected_package and selected_package.status == "published") else None,
        sent=sent,
        page_title="Contact Us | Travel Karo",
        meta_description="Get in touch with Travel Karo, Bathinda — call, WhatsApp or send an enquiry and our team will help plan your trip.",
    )
    return templates.TemplateResponse("public/contact.html", ctx)


@router.post("/enquiry")
def submit_enquiry(
    request: Request,
    db: Session = Depends(get_db),
    customer_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    interested_service: str = Form(""),
    destination: str = Form(""),
    travel_date: str = Form(""),
    num_travellers: str = Form(""),
    message: str = Form(""),
    package_id: str = Form(""),
    package_name: str = Form(""),
    company: str = Form(""),  # honeypot — real users never fill this
):
    """Handle every public enquiry → save it → it instantly becomes a CRM lead."""
    # 1. Spam defences: honeypot + required fields + rate limit.
    if company.strip():
        return RedirectResponse("/contact?sent=1", status_code=303)  # silently drop bots

    client_ip = request.client.host if request.client else "unknown"
    if too_many_submissions(client_ip):
        ctx = base_context(request)
        ctx["error"] = "You've sent several enquiries recently. Please try again shortly."
        ctx["page_title"] = "Contact Us | Travel Karo"
        return templates.TemplateResponse("public/contact.html", ctx, status_code=429)

    name = customer_name.strip()
    phone_clean = phone.strip()
    if not name or not phone_clean:
        ctx = base_context(request)
        ctx["error"] = "Please enter your name and phone number."
        ctx["page_title"] = "Contact Us | Travel Karo"
        return templates.TemplateResponse("public/contact.html", ctx, status_code=400)

    # 2. Work out the enquiry source and linked package.
    pkg = None
    if package_id.strip().isdigit():
        pkg = db.get(Package, int(package_id))

    if pkg is not None:
        source = "Package Booking"
    elif interested_service.strip():
        source = "Service Enquiry"
    else:
        source = "Contact Form"

    # 3. Parse optional values safely.
    t_date = None
    if travel_date.strip():
        try:
            t_date = datetime.strptime(travel_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            t_date = None

    travellers = None
    if num_travellers.strip().isdigit():
        travellers = int(num_travellers.strip())

    service = interested_service.strip() if interested_service in SERVICES else (
        interested_service.strip() or None
    )

    # 4. Save — this single insert is what makes it appear in the admin CRM.
    enquiry = Enquiry(
        customer_name=name,
        phone=phone_clean,
        email=email.strip() or None,
        interested_service=service,
        destination=destination.strip() or None,
        package_id=pkg.id if pkg else None,
        package_name=(pkg.title if pkg else (package_name.strip() or None)),
        travel_date=t_date,
        num_travellers=travellers,
        message=message.strip() or None,
        source=source,
        status="New",
    )
    db.add(enquiry)
    db.commit()

    return RedirectResponse("/contact?sent=1", status_code=303)
