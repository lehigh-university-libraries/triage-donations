# Book Donation Triage Scanner

STUB -- UNDER DEVELOPMENT

A Flask app for a book-donation triage desk. A librarian scans a book's ISBN
with a USB barcode scanner; the app checks local (Lehigh) holdings first via
SRU, falls back to a Library of Congress SRU lookup for title/author/Dewey
call number, maps the call number to a subject-selector librarian, and logs
every scan to a Google Sheet.

