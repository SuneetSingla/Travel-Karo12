"""Admin area: login, dashboard, package manager, CRM, settings. All protected."""
from datetime import datetime, date, timedelta
from collections import OrderedDict

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Package, Enquiry, EnquiryNote, BusinessSettings, Admin,
    PACKAGE_STATUSES, LEAD_STATUSES, SERVICES,
)
from ..templating import templates, base_context
from ..auth import require_admin, get_current_admin, verify_password, hash_password
from ..utils import save_package_image, delete_image_file

router = APIRouter(prefix="/admin")


# ======================================================================
# AUTH
# ======================================================================
@router.get("/login")
def login_page(request: Request):
    ctx = base_context(request)
    ctx["page_title"] = "Admin Login | Travel Karo"
    return templates.TemplateResponse("admin/login.html", ctx)


@router.post("/login")
def login(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
):
    admin = db.scalar(select(Admin).where(Admin.email == email.strip().lower()))
    if admin is None or not verify_password(password, admin.password_hash):
        ctx = base_context(request)
        ctx["error"] = "Incorrect email or password."
        ctx["page_title"] = "Admin Login | Travel Karo"
        return templates.TemplateResponse("admin/login.html", ctx, status_code=401)
    request.session["admin_id"] = admin.id
    return RedirectResponse("/admin", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


# ======================================================================
# OVERVIEW / DASHBOARD
# ======================================================================
@router.get("")
def dashboard(request: Request, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)):
    ctx = base_context(request)

    total_enquiries = db.scalar(select(func.count(Enquiry.id))) or 0
    new_enquiries = db.scalar(select(func.count(Enquiry.id)).where(Enquiry.status == "New")) or 0
    pending = db.scalar(
        select(func.count(Enquiry.id)).where(
            Enquiry.status.in_(["New", "Contacted", "Follow-up Required", "Quotation Sent"])
        )
    ) or 0
    confirmed = db.scalar(select(func.count(Enquiry.id)).where(Enquiry.status == "Confirmed")) or 0
    published = db.scalar(select(func.count(Package.id)).where(Package.status == "published")) or 0
    unpublished = db.scalar(select(func.count(Package.id)).where(Package.status == "draft")) or 0

    month_start = date.today().replace(day=1)
    this_month = db.scalar(
        select(func.count(Enquiry.id)).where(Enquiry.created_at >= month_start)
    ) or 0

    # --- Chart data ---------------------------------------------------
    # 1) Enquiries over the last 6 months
    months = OrderedDict()
    today = date.today()
    for i in range(5, -1, -1):
        m = (today.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        months[m.strftime("%b %Y")] = 0
    for e in db.scalars(select(Enquiry)).all():
        key = e.created_at.strftime("%b %Y")
        if key in months:
            months[key] += 1

    # 2) By service
    by_service = OrderedDict((s, 0) for s in SERVICES)
    by_service["Other"] = 0
    for e in db.scalars(select(Enquiry)).all():
        if e.interested_service in by_service:
            by_service[e.interested_service] += 1
        else:
            by_service["Other"] += 1

    # 3) By status
    by_status = OrderedDict((s, 0) for s in LEAD_STATUSES)
    for s in LEAD_STATUSES:
        by_status[s] = db.scalar(
            select(func.count(Enquiry.id)).where(Enquiry.status == s)
        ) or 0

    recent = db.scalars(select(Enquiry).order_by(Enquiry.created_at.desc()).limit(8)).all()

    # Follow-ups due (today or overdue, still open)
    followups = db.scalars(
        select(Enquiry)
        .where(Enquiry.follow_up_date.is_not(None))
        .where(Enquiry.follow_up_date <= date.today())
        .where(Enquiry.status.notin_(["Confirmed", "Closed / Not Interested"]))
        .order_by(Enquiry.follow_up_date.asc())
    ).all()

    ctx.update(
        stats=dict(
            total=total_enquiries, new=new_enquiries, pending=pending,
            confirmed=confirmed, published=published, unpublished=unpublished,
            this_month=this_month,
        ),
        chart_months_labels=list(months.keys()),
        chart_months_values=list(months.values()),
        chart_service_labels=[k for k in by_service],
        chart_service_values=[by_service[k] for k in by_service],
        chart_status_labels=list(by_status.keys()),
        chart_status_values=list(by_status.values()),
        recent=recent,
        followups=followups,
        active="overview",
        page_title="Dashboard | Travel Karo Admin",
    )
    return templates.TemplateResponse("admin/dashboard.html", ctx)


# ======================================================================
# PACKAGES
# ======================================================================
@router.get("/packages")
def admin_packages(request: Request, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)):
    ctx = base_context(request)
    ctx["packages"] = db.scalars(select(Package).order_by(Package.created_at.desc())).all()
    ctx["active"] = "packages"
    ctx["page_title"] = "Manage Packages | Travel Karo Admin"
    return templates.TemplateResponse("admin/packages_list.html", ctx)


@router.get("/packages/new")
def new_package_form(request: Request, admin: Admin = Depends(require_admin)):
    ctx = base_context(request)
    ctx.update(pkg=None, active="packages", page_title="Add Package | Travel Karo Admin")
    return templates.TemplateResponse("admin/package_form.html", ctx)


@router.get("/packages/{package_id}/edit")
def edit_package_form(package_id: int, request: Request, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)):
    pkg = db.get(Package, package_id)
    if pkg is None:
        return RedirectResponse("/admin/packages", status_code=303)
    ctx = base_context(request)
    ctx.update(pkg=pkg, active="packages", page_title="Edit Package | Travel Karo Admin")
    return templates.TemplateResponse("admin/package_form.html", ctx)


def _parse_price(raw: str):
    raw = (raw or "").replace(",", "").strip()
    try:
        return float(raw) if raw else None
    except ValueError:
        return None


@router.post("/packages/save")
async def save_package(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
    package_id: str = Form(""),
    title: str = Form(...),
    destination: str = Form(""),
    short_description: str = Form(""),
    full_description: str = Form(""),
    duration: str = Form(""),
    starting_price: str = Form(""),
    included_services: str = Form(""),
    exclusions: str = Form(""),
    itinerary: str = Form(""),
    additional_info: str = Form(""),
    status: str = Form("draft"),
    remove_images: list[str] = Form([]),
    images: list[UploadFile] = File([]),
):
    pkg = db.get(Package, int(package_id)) if package_id.strip().isdigit() else None
    is_new = pkg is None
    if is_new:
        pkg = Package(images=[])
        db.add(pkg)

    pkg.title = title.strip()
    pkg.destination = destination.strip() or None
    pkg.short_description = short_description.strip() or None
    pkg.full_description = full_description.strip() or None
    pkg.duration = duration.strip() or None
    pkg.starting_price = _parse_price(starting_price)
    pkg.included_services = included_services.strip() or None
    pkg.exclusions = exclusions.strip() or None
    pkg.itinerary = itinerary.strip() or None
    pkg.additional_info = additional_info.strip() or None
    pkg.status = status if status in PACKAGE_STATUSES else "draft"

    # Remove any images the admin unchecked.
    current = list(pkg.images or [])
    for img in remove_images:
        if img in current:
            current.remove(img)
            delete_image_file(img)

    # Add newly uploaded images.
    for up in images:
        if up and up.filename:
            current.append(save_package_image(up))
    pkg.images = current

    db.commit()
    return RedirectResponse("/admin/packages", status_code=303)


@router.post("/packages/{package_id}/status")
def toggle_status(package_id: int, request: Request, db: Session = Depends(get_db), admin: Admin = Depends(require_admin), to: str = Form(...)):
    pkg = db.get(Package, package_id)
    if pkg and to in PACKAGE_STATUSES:
        pkg.status = to
        db.commit()
    return RedirectResponse("/admin/packages", status_code=303)


@router.post("/packages/{package_id}/delete")
def delete_package(package_id: int, request: Request, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)):
    pkg = db.get(Package, package_id)
    if pkg:
        for img in (pkg.images or []):
            delete_image_file(img)
        db.delete(pkg)
        db.commit()
    return RedirectResponse("/admin/packages", status_code=303)


@router.get("/packages/{package_id}/preview")
def preview_package(package_id: int, request: Request, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)):
    pkg = db.get(Package, package_id)
    if pkg is None:
        return RedirectResponse("/admin/packages", status_code=303)
    ctx = base_context(request)
    ctx.update(pkg=pkg, preview=True, page_title=f"Preview: {pkg.title}")
    return templates.TemplateResponse("public/package_detail.html", ctx)


# ======================================================================
# ENQUIRIES & CRM
# ======================================================================
@router.get("/enquiries")
def enquiries_list(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
    q: str = "",
    status: str = "",
    service: str = "",
    period: str = "",
):
    stmt = select(Enquiry)
    if q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where((Enquiry.customer_name.ilike(like)) | (Enquiry.phone.ilike(like)))
    if status in LEAD_STATUSES:
        stmt = stmt.where(Enquiry.status == status)
    if service:
        stmt = stmt.where(Enquiry.interested_service == service)
    if period == "7":
        stmt = stmt.where(Enquiry.created_at >= datetime.now() - timedelta(days=7))
    elif period == "30":
        stmt = stmt.where(Enquiry.created_at >= datetime.now() - timedelta(days=30))

    leads = db.scalars(stmt.order_by(Enquiry.created_at.desc())).all()

    ctx = base_context(request)
    ctx.update(
        leads=leads, q=q, f_status=status, f_service=service, f_period=period,
        active="enquiries", page_title="Enquiries & CRM | Travel Karo Admin",
    )
    return templates.TemplateResponse("admin/enquiries_list.html", ctx)


@router.get("/enquiries/{enquiry_id}")
def enquiry_detail(enquiry_id: int, request: Request, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)):
    lead = db.get(Enquiry, enquiry_id)
    if lead is None:
        return RedirectResponse("/admin/enquiries", status_code=303)
    ctx = base_context(request)
    ctx.update(lead=lead, active="enquiries", page_title=f"{lead.customer_name} | CRM")
    return templates.TemplateResponse("admin/enquiry_detail.html", ctx)


@router.post("/enquiries/{enquiry_id}/update")
def update_enquiry(
    enquiry_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
    status: str = Form(""),
    follow_up_date: str = Form(""),
    customer_name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
    destination: str = Form(""),
):
    lead = db.get(Enquiry, enquiry_id)
    if lead is None:
        return RedirectResponse("/admin/enquiries", status_code=303)
    if status in LEAD_STATUSES:
        lead.status = status
    lead.follow_up_date = (
        datetime.strptime(follow_up_date, "%Y-%m-%d").date() if follow_up_date.strip() else None
    )
    if customer_name.strip():
        lead.customer_name = customer_name.strip()
    if phone.strip():
        lead.phone = phone.strip()
    lead.email = email.strip() or None
    lead.destination = destination.strip() or None
    db.commit()
    return RedirectResponse(f"/admin/enquiries/{enquiry_id}", status_code=303)


@router.post("/enquiries/{enquiry_id}/note")
def add_note(enquiry_id: int, request: Request, db: Session = Depends(get_db), admin: Admin = Depends(require_admin), note: str = Form(...)):
    lead = db.get(Enquiry, enquiry_id)
    if lead and note.strip():
        db.add(EnquiryNote(enquiry_id=lead.id, note=note.strip()))
        db.commit()
    return RedirectResponse(f"/admin/enquiries/{enquiry_id}", status_code=303)


@router.post("/enquiries/{enquiry_id}/delete")
def delete_enquiry(enquiry_id: int, request: Request, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)):
    lead = db.get(Enquiry, enquiry_id)
    if lead:
        db.delete(lead)
        db.commit()
    return RedirectResponse("/admin/enquiries", status_code=303)


# ======================================================================
# SETTINGS
# ======================================================================
@router.get("/settings")
def settings_page(request: Request, db: Session = Depends(get_db), admin: Admin = Depends(require_admin), saved: str = "", pwd: str = ""):
    ctx = base_context(request)
    ctx.update(active="settings", saved=saved, pwd=pwd, page_title="Settings | Travel Karo Admin")
    return templates.TemplateResponse("admin/settings.html", ctx)


@router.post("/settings")
def update_settings(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
    phone: str = Form(""),
    email: str = Form(""),
    address: str = Form(""),
    website: str = Form(""),
    instagram: str = Form(""),
    facebook: str = Form(""),
):
    biz = db.get(BusinessSettings, 1)
    biz.phone = phone.strip() or None
    biz.email = email.strip() or None
    biz.address = address.strip() or None
    biz.website = website.strip() or None
    biz.instagram = instagram.strip() or None
    biz.facebook = facebook.strip() or None
    db.commit()
    return RedirectResponse("/admin/settings?saved=1", status_code=303)


@router.post("/settings/password")
def change_password(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    if not verify_password(current_password, admin.password_hash):
        return RedirectResponse("/admin/settings?pwd=wrong", status_code=303)
    if len(new_password) < 8 or new_password != confirm_password:
        return RedirectResponse("/admin/settings?pwd=invalid", status_code=303)
    admin.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse("/admin/settings?pwd=ok", status_code=303)
