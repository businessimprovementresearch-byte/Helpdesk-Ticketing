from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Kirim email tes buat debug konfigurasi SMTP (error TIDAK ditelan/fail_silently)."

    def add_arguments(self, parser):
        parser.add_argument("to", type=str, help="crmla.g062gmail.com")

    def handle(self, *args, **options):
        to = options["to"]

        self.stdout.write(self.style.WARNING("=== Konfigurasi email yang terbaca dari settings ==="))
        self.stdout.write(f"EMAIL_BACKEND      = {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST         = {settings.EMAIL_HOST}")
        self.stdout.write(f"EMAIL_PORT         = {settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_USE_SSL      = {settings.EMAIL_USE_SSL}")
        self.stdout.write(f"EMAIL_USE_TLS      = {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"EMAIL_HOST_USER    = {settings.EMAIL_HOST_USER!r}")
        self.stdout.write(f"EMAIL_HOST_PASSWORD= {'(kosong)' if not settings.EMAIL_HOST_PASSWORD else '*' * len(settings.EMAIL_HOST_PASSWORD)}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL = {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"TICKET_NOTIFICATION_CC = {settings.TICKET_NOTIFICATION_CC}")
        self.stdout.write("")

        if settings.EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
            raise CommandError(
                "EMAIL_BACKEND masih 'console' — artinya EMAIL_HOST_USER kebaca KOSONG "
                "oleh Django (lihat settings.py baris 'if not EMAIL_HOST_USER'). "
                "Cek lagi isi file .env kamu, dan pastikan server di-restart setelah edit .env "
                "(load_dotenv() cuma jalan sekali saat proses Django start)."
            )

        self.stdout.write(f"Mencoba kirim email tes ke {to} ...")
        try:
            email = EmailMessage(
                subject="[Test] Konfigurasi email Helpdesk Selectro",
                body="Kalau kamu terima email ini, konfigurasi SMTP kamu sudah benar.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to],
            )
            email.send(fail_silently=False)
        except Exception as exc:
            raise CommandError(f"GAGAL kirim email. Error asli dari server SMTP:\n\n{exc!r}") from exc

        self.stdout.write(self.style.SUCCESS(f"Email tes berhasil dikirim ke {to}."))