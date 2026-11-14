"""Public website routes: Home, Destinations, About, Contact + enquiry submit."""
from datetime import datetime

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Package, Enquiry, ClickEvent, SERVICES, CLICK_KINDS
from ..templating import templates, base_context

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
    ctx["featured"] = published_packages(db, limit=4)
    ctx["page_title"] = "Travel Karo — Your Journey, Our Passion | Bathinda Travel Agency"
    ctx["meta_description"] = (
        "Travel Karo, Bathinda — air tickets, hotels, visas, holiday packages, "
        "cruises, insurance & IRCTC railway tickets. Explore domestic & "
        "international destinations. Let's make memories."
    )
    return templates.TemplateResponse("public/home.html", ctx)


@router.get("/packages")
def packages(request: Request, db: Session = Depends(get_db)):
    ctx = base_context(request)
    pkgs = published_packages(db)
    ctx["packages"] = pkgs
    ctx["has_domestic"] = any(p.category == "domestic" for p in pkgs)
    ctx["has_international"] = any(p.category == "international" for p in pkgs)
    ctx["page_title"] = "Destinations & Holiday Packages | Travel Karo"
    ctx["meta_description"] = (
        "Explore domestic and international destinations and holiday packages from "
        "Travel Karo — tailored to your dates and budget."
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


@router.get("/about")
def about(request: Request):
    ctx = base_context(request)
    ctx["page_title"] = "About Us | Travel Karo"
    ctx["meta_description"] = (
        "Travel Karo is an IRCTC-authorised, GST-registered family travel agency in "
        "Bathinda, offering personal service for flights, stays, visas and holidays."
    )
    return templates.TemplateResponse("public/about.html", ctx)


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
        selected_package=selected_package
        if (selected_package and selected_package.status == "published") else None,
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
    from ..utils import too_many_submissions  # local import keeps module load light

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

    pkg = db.get(Package, int(package_id)) if package_id.strip().isdigit() else None
    if pkg is not None:
        source = "Package Booking"
    elif interested_service.strip():
        source = "Service Enquiry"
    else:
        source = "Contact Form"

    t_date = None
    if travel_date.strip():
        try:
            t_date = datetime.strptime(travel_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            t_date = None

    travellers = int(num_travellers.strip()) if num_travellers.strip().isdigit() else None

    enquiry = Enquiry(
        customer_name=name,
        phone=phone_clean,
        email=email.strip() or None,
        interested_service=interested_service.strip() or None,
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


@router.post("/track")
async def track_click(request: Request, db: Session = Depends(get_db)):
    """Lightweight click tracking for website-performance insights.

    Called from the public pages via navigator.sendBeacon when a visitor clicks
    WhatsApp / Call / Book / Enquire etc. Stores no personal data.
    """
    try:
        data = await request.json()
    except Exception:
        data = {}
    kind = str(data.get("kind", "")).strip()
    label = str(data.get("label", "")).strip()[:200] or None
    if kind in CLICK_KINDS:
        db.add(ClickEvent(kind=kind, label=label))
        db.commit()
    return Response(status_code=204)
