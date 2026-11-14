# Testing

An automated end-to-end test (`tests/test_app.py`) verifies the whole app against
the project's requirements. Run it any time:

```bash
. .venv/bin/activate
pip install httpx          # test-only dependency
PYTHONPATH=. python tests/test_app.py
```

It uses a temporary throwaway database and checks all of the following — every
item passed when this project was delivered:

| # | Requirement | Result |
|---|-------------|--------|
| 1 | Home, Packages, Contact pages load | ✅ |
| 2 | robots.txt disallows /admin; sitemap.xml generated | ✅ |
| 3 | Admin pages are blocked for logged-out visitors (redirect to login) | ✅ |
| 4 | Contact-form submission creates a CRM lead automatically | ✅ |
| 5 | Lead source is detected correctly (Contact / Service / Package) | ✅ |
| 6 | Honeypot silently blocks bot submissions | ✅ |
| 7 | Wrong password rejected; correct password logs in | ✅ |
| 8 | Admin dashboard & enquiries list load after login | ✅ |
| 9 | Admin can add a package with an uploaded image | ✅ |
| 10 | Publishing a package makes it visible on the public site | ✅ |
| 11 | Unpublishing hides it from the public site (detail → 404) | ✅ |
| 12 | "Book This Package" enquiry links the lead to the package | ✅ |
| 13 | Admin can add internal notes to a lead | ✅ |
| 14 | Admin can change a lead's status and set a follow-up date | ✅ |
| 15 | Deleting a package keeps its past booking leads intact | ✅ |

Mobile responsiveness is handled in CSS (`app/static/css/styles.css`) with
breakpoints at 960px, 760px and 480px, including a collapsible nav and a
slide-in admin sidebar.
