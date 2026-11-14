"""Create (or reset) the Travel Karo admin login.

Run this once after setup:

    python create_admin.py

It asks for an email and password and saves the admin account. Run it again
any time to add another admin or reset a password for an existing email.
There is no public sign-up anywhere on the website — this script is the only
way an admin account is created.
"""
import getpass
import sys

from app.database import Base, engine, SessionLocal
from app.models import Admin
from app.auth import hash_password

Base.metadata.create_all(bind=engine)


def main() -> None:
    print("\n=== Travel Karo — create admin account ===\n")
    email = input("Admin email: ").strip().lower()
    if not email or "@" not in email:
        sys.exit("A valid email is required.")

    password = getpass.getpass("Password (min 8 characters): ")
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters.")
    if password != getpass.getpass("Confirm password: "):
        sys.exit("Passwords did not match.")

    db = SessionLocal()
    try:
        existing = db.query(Admin).filter(Admin.email == email).first()
        if existing:
            existing.password_hash = hash_password(password)
            print(f"\n✓ Password updated for existing admin: {email}")
        else:
            db.add(Admin(email=email, password_hash=hash_password(password)))
            print(f"\n✓ Admin created: {email}")
        db.commit()
        print("You can now log in at /admin/login\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
