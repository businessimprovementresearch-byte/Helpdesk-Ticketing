# Helpdesk Ticketing

Sistem ticketing internal, dibangun dari nol pakai Django, terinspirasi dari
struktur Selectro Helpdesk (Laravel). Database & file storage pakai Supabase,
hosting pakai Render.

## Stack
- Django 5.2 (built-in auth, role: admin/agent/customer)
- PostgreSQL via Supabase
- File attachment via Supabase Storage (S3-compatible)
- Email keluar: SMTP | Email masuk jadi tiket: IMAP (management command `fetch_emails`)
- Hosting: Render (web service + cron job)

## Setup Lokal

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # lalu isi manual field-field di dalamnya
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Buka http://127.0.0.1:8000 — otomatis redirect ke halaman tickets (perlu login dulu).

Secara default (`PRODUCTION=False` di `.env`), pakai SQLite lokal & local file
storage, jadi kamu bisa develop tanpa perlu isi kredensial Supabase dulu.

## Menjalankan fetch_emails secara manual (testing)

```bash
python manage.py fetch_emails
```

Cek inbox IMAP, ubah email unread jadi tiket baru (atau balasan tiket lama
kalau subject-nya ada tag `[Ticket #<id>]`).

## Struktur Role

- **admin** — akses penuh, termasuk halaman Users
- **agent** — bisa lihat & balas semua tiket, termasuk internal note
- **customer** — cuma bisa lihat & balas tiket miliknya sendiri, tidak bisa lihat internal note

Set role & division lewat Django Admin (`/admin/`) setelah user dibuat.

## Deploy ke Render

1. Push project ini ke GitHub
2. Di Render dashboard: **New > Blueprint**, connect ke repo ini — Render akan
   otomatis baca `render.yaml` dan bikin 2 service: web service + cron job
3. Isi environment variables yang ditandai `sync: false` di `render.yaml`
   (Render akan minta diisi manual pas pertama kali provision):
   - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` — dari Supabase (Settings > Database)
   - `SUPABASE_S3_ACCESS_KEY_ID`, `SUPABASE_S3_SECRET_ACCESS_KEY`, `SUPABASE_S3_ENDPOINT_URL`, `SUPABASE_S3_REGION` — dari Supabase (Settings > Storage > S3 Connection)
   - `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` — kredensial SMTP
   - `IMAP_USERNAME`, `IMAP_PASSWORD` — kredensial IMAP
4. Deploy. Setelah live, jalankan `createsuperuser` lewat Render Shell:
   `python manage.py createsuperuser`
5. Cek log cron job (`fetch-emails`) untuk mastiin proses IMAP fetch jalan
   tiap 10 menit tanpa error

## Catatan Biaya Render

- Web service: gratis di free tier, tapi idle 15 menit = spin down (cold start
  ~1 menit pas diakses lagi). Upgrade ke Starter ($7/bulan) kalau mau always-on.
- Cron job: minimum charge $1/bulan (dihitung per detik waktu eksekusi aktual)
