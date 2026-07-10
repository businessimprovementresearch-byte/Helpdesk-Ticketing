import uuid

from django.conf import settings
from django.db import models


class Ticket(models.Model):
    """Tiket utama — setara dengan tabel `tickets` di Selectro Helpdesk."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        PENDING = "pending", "Pending"
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Source(models.TextChoices):
        WEB = "web", "Web"
        EMAIL = "email", "Email"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ticket_code = models.CharField(max_length=20, unique=True, blank=True, db_index=True)
    subject = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.WEB)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="tickets_created",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tickets_assigned",
    )
    division = models.ForeignKey(
        "accounts.Division", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tickets",
    )

    # Field tambahan spesifik bisnis (setara no_sj, salesman, invoice_status,
    # nama_perusahaan di Selectro Helpdesk lama)
    nama_perusahaan = models.CharField(max_length=255, blank=True)
    no_sj = models.CharField(max_length=100, blank=True)
    salesman = models.CharField(max_length=100, blank=True)
    invoice_status = models.CharField(max_length=100, blank=True)

    # Dipakai untuk mencocokkan balasan email masuk ke tiket yang sudah ada
    email_message_id = models.CharField(max_length=255, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.subject}"

    @classmethod
    def generate_ticket_code(cls, division=None):
        """Kalau ada divisi, delegasikan ke Division.generate_next_ticket_code().
        Kalau tidak (mis. tiket dari email tanpa divisi), pakai prefix 'GN-xxx'."""
        from django.db import transaction

        if division is not None:
            return division.generate_next_ticket_code()

        with transaction.atomic():
            last_ticket = (
                cls.objects.select_for_update()
                .filter(ticket_code__startswith="GN-")
                .order_by("-ticket_code")
                .first()
            )
            next_number = 1
            if last_ticket and "-" in last_ticket.ticket_code:
                try:
                    next_number = int(last_ticket.ticket_code.rsplit("-", 1)[-1]) + 1
                except ValueError:
                    pass
            return f"GN-{next_number:03d}"


class TicketReply(models.Model):
    """Balasan/komentar pada tiket — public_reply (terlihat customer) vs internal_note."""

    class Type(models.TextChoices):
        PUBLIC_REPLY = "public_reply", "Public Reply"
        INTERNAL_NOTE = "internal_note", "Internal Note"

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="ticket_replies"
    )
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.PUBLIC_REPLY)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply on {self.ticket.subject} ({self.type})"


def attachment_upload_path(instance, filename):
    return f"tickets/{instance.reply.ticket_id}/{instance.reply_id}/{filename}"


class Attachment(models.Model):
    """File lampiran, disimpan di Supabase Storage lewat django-storages."""

    reply = models.ForeignKey(TicketReply, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=attachment_upload_path)
    file_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name
