# CAK Tracker V23 — W3Schools Django starter

Upload the **contents** of this ZIP into your existing Python Space, retaining the folder structure. Back up your Space first. This replaces `blank/templates/index.html`, `blank/views.py`, `blank/models.py`, `blank/urls.py` and adds `blank/migrations/0001_initial.py`.

## Before public use
1. Set `CAK_ADMIN_PASSWORD_HASH` to a Django PBKDF2 password hash, generated with `python manage.py shell -c "from django.contrib.auth.hashers import make_password; print(make_password(input('Admin password: ')))"`. The app **does not** ship with a default admin password. Do not paste passwords into public code.
2. Set Django `SECRET_KEY` through secure environment configuration, ensure `DEBUG=False`, correct `ALLOWED_HOSTS`, HTTPS, secure session cookies, and a backed-up persistent database. Verify W3Schools supports these settings.
3. Run `python manage.py migrate`. Admin account `EAdmin` is created by the migration.
4. Test EAdmin sign-in, create one test employee, sign in as employee, save a test photo, log out, log back in, and confirm admin can see the record.

**Security:** Employee E-number-only login is not identity verification. Anyone knowing another employee's E-number can impersonate them. Use only with employer approval and appropriate access controls. Fleet photos and VINs may be sensitive business data. Database-stored photos grow quickly; verify hosting quotas and backup strategy.

This is a Django port of V22. It has not been tested on W3Schools hosting. Old locally stored records are not automatically migrated.
