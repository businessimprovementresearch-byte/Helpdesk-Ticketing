# Project Index

## 1. Project overview

This repository is a Django-based internal helpdesk and ticketing system inspired by Selectro Helpdesk. It supports multi-role access, ticket workflows, email-based ticket creation, and reporting for operations teams.

Core technologies:

- Django 5.2
- PostgreSQL in production (Supabase-compatible)
- SQLite for local development
- Django custom user model with role-based access
- Attachment storage via Supabase S3-compatible storage or local filesystem
- Email integration via Gmail API / SMTP / Resend
- IMAP polling for inbound email-to-ticket conversion

---

## 2. Repository map

### Root files

- [manage.py](manage.py) — Django project entry point.
- [build.sh](build.sh) — deployment helper script.
- [requirements.txt](requirements.txt) — Python dependencies.
- [render.yaml](render.yaml) — Render deployment config.
- [env.example](env.example) — environment variables template.
- [README.md](README.md) — project setup and deployment notes.
- [client_secret.json](client_secret.json) — Gmail OAuth client config (if used locally).
- [get_gmail_refresh_token.py](get_gmail_refresh_token.py) — helper script to obtain a Gmail refresh token.

### Django project config

- [helpdesk_ticketing/settings.py](helpdesk_ticketing/settings.py) — settings, DB config, email config, storage config, auth setup.
- [helpdesk_ticketing/urls.py](helpdesk_ticketing/urls.py) — root URL routing and auth/login routes.
- [helpdesk_ticketing/asgi.py](helpdesk_ticketing/asgi.py) — ASGI app entry.
- [helpdesk_ticketing/wsgi.py](helpdesk_ticketing/wsgi.py) — WSGI app entry.

### App: accounts

- [accounts/models.py](accounts/models.py) — custom user model and Division model.
- [accounts/views.py](accounts/views.py) — user profile/password settings views.
- [accounts/forms.py](accounts/forms.py) — authentication and profile form logic.
- [accounts/backends.py](accounts/backends.py) — custom email-based login backend.
- [accounts/urls.py](accounts/urls.py) — settings routes.
- [accounts/admin.py](accounts/admin.py) — admin registrations.
- [accounts/tests.py](accounts/tests.py) — app tests.
- [accounts/management/commands/seed_initial_users.py](accounts/management/commands/seed_initial_users.py) — seeding initial roles/users.

### App: tickets

- [tickets/models.py](tickets/models.py) — Ticket, TicketReply, Attachment models.
- [tickets/views.py](tickets/views.py) — ticket dashboard, detail, forms, reports, export, email webhook.
- [tickets/urls.py](tickets/urls.py) — ticket routes, admin/report routes.
- [tickets/forms.py](tickets/forms.py) — ticket/user/division forms.
- [tickets/emails.py](tickets/emails.py) — email notification logic.
- [tickets/gmail_api_backend.py](tickets/gmail_api_backend.py) — Gmail API mail backend.
- [tickets/management/commands/fetch_emails.py](tickets/management/commands/fetch_emails.py) — IMAP email polling command.
- [tickets/management/commands/send_test_email.py](tickets/management/commands/send_test_email.py) — email smoke-test command.
- [tickets/templatetags/ticket_extras.py](tickets/templatetags/ticket_extras.py) — template filters/helpers.

### Templates

- [templates/base.html](templates/base.html) — global layout.
- [templates/registration/login.html](templates/registration/login.html) — login page.
- [templates/accounts/settings_base.html](templates/accounts/settings_base.html) — profile settings shell.
- [templates/accounts/settings_profile.html](templates/accounts/settings_profile.html) — profile edit page.
- [templates/accounts/settings_password.html](templates/accounts/settings_password.html) — password change page.
- [templates/tickets/dashboard.html](templates/tickets/dashboard.html) — main dashboard.
- [templates/tickets/index.html](templates/tickets/index.html) — list of tickets.
- [templates/tickets/ticket_detail.html](templates/tickets/ticket_detail.html) — ticket conversation and replies.
- [templates/tickets/ticket_form.html](templates/tickets/ticket_form.html) — create/edit ticket form.
- [templates/tickets/user_form.html](templates/tickets/user_form.html) — user create/edit form.
- [templates/tickets/users_index.html](templates/tickets/users_index.html) — user management page.
- [templates/tickets/division_form.html](templates/tickets/division_form.html) — division form.
- [templates/tickets/divisions_index.html](templates/tickets/divisions_index.html) — divisions listing.
- [templates/tickets/reports_index.html](templates/tickets/reports_index.html) — reports dashboard.
- [templates/emails/ticket_notification.html](templates/emails/ticket_notification.html) — email notification template.

---

## 3. Core domain model

### User and role system

- The project uses a custom user model: [accounts/models.py](accounts/models.py).
- Roles are defined as: admin, agent, customer.
- Authentication is customized to allow login by email: [accounts/backends.py](accounts/backends.py), [accounts/forms.py](accounts/forms.py).

### Division model

- A Division groups users and tickets by department.
- Each division can generate sequential ticket codes such as `OPS-001`.

### Ticket model

- [tickets/models.py](tickets/models.py) defines the main Ticket model.
- Important fields include:
  - `subject`, `status`, `priority`, `source`
  - `created_by`, `assigned_to`, `division`
  - `ticket_code`, `email_message_id`
  - `nama_perusahaan`, `no_sj`, `salesman`, `invoice_status`
- Ticket replies are recorded as `TicketReply` entries with `PUBLIC_REPLY` or `INTERNAL_NOTE` types.
- Attachments are stored via `Attachment` with upload path logic.

---

## 4. Route map

### Main site routes

- `GET /` → redirects to the dashboard
- `GET /tickets/` → ticket list
- `GET /tickets/dashboard/` → dashboard page
- `GET /tickets/create/` → create ticket
- `GET /tickets/<pk>/` → ticket detail
- `GET /tickets/users/` → user management (admin)
- `GET /tickets/divisions/` → divisions management
- `GET /tickets/reports/` → reports page
- `GET /cron/fetch-emails/` → email webhook trigger

### Auth routes

- `/accounts/login/`
- `/accounts/logout/`
- `/accounts/password/...` via Django auth URLs

---

## 5. Key operational workflows

### Local development

1. Create and activate a virtual environment.
2. Install dependencies via `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and fill required values.
4. Run migrations.
5. Create a superuser.
6. Run the Django server.

### Email-to-ticket workflow

- [tickets/management/commands/fetch_emails.py](tickets/management/commands/fetch_emails.py) polls IMAP inboxes.
- New email threads become tickets automatically.
- Replies to existing tickets can match by subject tags like `[Ticket #<id>]`.

### Reporting and export

- Views under [tickets/views.py](tickets/views.py) support report generation and Excel export.

### Storage and email configuration

- [helpdesk_ticketing/settings.py](helpdesk_ticketing/settings.py) switches between:
  - SQLite + local filesystem for local dev
  - PostgreSQL + Supabase storage for production
  - Gmail API, Resend, or SMTP for outbound email

---

## 6. Best starting points for reading code

If you are new to this codebase, read in this order:

1. [helpdesk_ticketing/settings.py](helpdesk_ticketing/settings.py)
2. [helpdesk_ticketing/urls.py](helpdesk_ticketing/urls.py)
3. [accounts/models.py](accounts/models.py)
4. [tickets/models.py](tickets/models.py)
5. [tickets/views.py](tickets/views.py)
6. [tickets/urls.py](tickets/urls.py)
7. [templates/tickets/dashboard.html](templates/tickets/dashboard.html)

---

## 7. Useful commands

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
python manage.py fetch_emails
python manage.py send_test_email
```

---

## 8. Notes

- The project is oriented around internal business support workflows rather than a generic SaaS ticket system.
- Developer environment defaults to local SQLite unless production environment variables are set.
- The app is designed to be deployable on Render with cron workers for IMAP polling.
