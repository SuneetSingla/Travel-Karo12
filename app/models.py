"""Database tables, as SQLAlchemy models.

Tables are created automatically on first run (see main.py), so there is no
separate SQL migration to run on localhost.
"""
from datetime import datetime, date
from sqlalchemy import String, Text, Integer, Numeric, Date, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Allowed values kept in one place so templates and routes stay in sync.
PACKAGE_STATUSES = ("draft", "published")
ENQUIRY_SOURCES = ("Contact Form", "Package Booking", "Service Enquiry")
LEAD_STATUSES = (
    "New",
    "Contacted",
    "Follow-up Required",
    "Quotation Sent",
    "Confirmed",
    "Closed / Not Interested",
)
SERVICES = (
    "Air Tickets",
    "Hotel Booking",
    "Visa Services",
    "Holiday Packages",
    "Cruise Bookings",
    "Travel Insurance",
    "Railway Tickets",
)
PACKAGE_CATEGORIES = ("domestic", "international")
# Allowed click-event kinds tracked for website performance insights.
CLICK_KINDS = ("whatsapp", "call", "book", "enquire", "view_package", "map")


class Admin(Base):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Package(Base):
    __tablename__ = "packages"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str | None] = mapped_column(String(200))
    short_description: Mapped[str | None] = mapped_column(Text)
    full_description: Mapped[str | None] = mapped_column(Text)
    duration: Mapped[str | None] = mapped_column(String(120))
    starting_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    # "domestic" or "international" — decides which tab it shows under.
    category: Mapped[str] = mapped_column(String(20), default="domestic", index=True)
    included_services: Mapped[str | None] = mapped_column(Text)  # one item per line
    exclusions: Mapped[str | None] = mapped_column(Text)         # one item per line
    itinerary: Mapped[str | None] = mapped_column(Text)
    additional_info: Mapped[str | None] = mapped_column(Text)
    # List of image file paths (served from /uploads). JSON works on SQLite + Postgres.
    images: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    enquiries: Mapped[list["Enquiry"]] = relationship(back_populates="package")

    @property
    def cover_image(self) -> str | None:
        return self.images[0] if self.images else None


class Enquiry(Base):
    __tablename__ = "enquiries"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(40), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    interested_service: Mapped[str | None] = mapped_column(String(120))
    destination: Mapped[str | None] = mapped_column(String(200))
    package_id: Mapped[int | None] = mapped_column(
        ForeignKey("packages.id", ondelete="SET NULL")
    )
    package_name: Mapped[str | None] = mapped_column(String(200))  # snapshot
    travel_date: Mapped[date | None] = mapped_column(Date)
    num_travellers: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(40), default="Contact Form")
    status: Mapped[str] = mapped_column(String(40), default="New", index=True)
    follow_up_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    package: Mapped["Package | None"] = relationship(back_populates="enquiries")
    notes: Mapped[list["EnquiryNote"]] = relationship(
        back_populates="enquiry", cascade="all, delete-orphan",
        order_by="EnquiryNote.created_at.desc()",
    )


class EnquiryNote(Base):
    __tablename__ = "enquiry_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    enquiry_id: Mapped[int] = mapped_column(
        ForeignKey("enquiries.id", ondelete="CASCADE")
    )
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    enquiry: Mapped["Enquiry"] = relationship(back_populates="notes")


class BusinessSettings(Base):
    __tablename__ = "business_settings"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    phone: Mapped[str | None] = mapped_column(String(60))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(255))
    instagram: Mapped[str | None] = mapped_column(String(255))
    facebook: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class PageView(Base):
    """One row per public page visit — powers the 'website reach' insights."""
    __tablename__ = "page_views"
    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(String(200), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)


class ClickEvent(Base):
    """One row per tracked click (WhatsApp, Call, Book, Enquire...) — powers
    the 'website performance / clicks' insights."""
    __tablename__ = "click_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    label: Mapped[str | None] = mapped_column(String(200))  # e.g. package name
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), index=True)
