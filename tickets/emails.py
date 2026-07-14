from django.conf import settings
from django.core.mail import EmailMessage

from .models import Ticket


def ticket_email_subject(ticket: Ticket) -> str:
    """Subject dengan tag [Ticket #ID] supaya balasan email bisa dicocokkan
    kembali ke tiket yang sama oleh management command fetch_emails."""
    return f"[Ticket #{ticket.id}] {ticket.subject}"


def _send(subject: str, message: str, to: list[str], cc: list[str] | None = None):
    """Helper kirim email + auto-CC ke TICKET_NOTIFICATION_CC (kalau ada)."""
    to = [e for e in to if e]
    if not to:
        return
    cc = [e for e in (cc or []) if e and e not in to]
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to,
        cc=cc or None,
    )
    email.send(fail_silently=True)


def send_new_ticket_notification(ticket: Ticket):
    """Kirim email konfirmasi ke pembuat tiket saat tiket baru dibuat, dengan
    CC ke alamat pemantauan (TICKET_NOTIFICATION_CC, mis. surat.selectro@gmail.com)."""
    if not (ticket.created_by and ticket.created_by.email):
        return
    _send(
        subject=ticket_email_subject(ticket),
        message=(
            f"Halo {ticket.created_by},\n\n"
            f"Tiket Anda telah berhasil dibuat. Berikut detailnya:\n\n"
            f"No. Referensi: {ticket.ticket_code}\n"
            f"Subjek Tiket: {ticket.subject}\n"
            f"Kategori: {ticket.category}\n"
            f"Prioritas: {ticket.get_priority_display()}\n\n"
            f"Tiket Anda sedang diproses. Tim kami akan segera meninjau dan "
            f"merespons tiket Anda dalam waktu 1x24 jam.\n\n"
            f"Terima kasih,\nTim Helpdesk Selectro"
        ),
        to=[ticket.created_by.email],
        cc=settings.TICKET_NOTIFICATION_CC,
    )


def send_status_change_notification(ticket, old_status, changed_by=None):
    """Kirim email ke customer pembuat tiket saat status tiket berubah."""
    if ticket.status == old_status:
        return
    if not (ticket.created_by and ticket.created_by.email):
        return
    # Kalau yang mengubah status adalah si customer sendiri (mis. auto-reopen
    # karena dia reply), tidak perlu kirim email ke dirinya sendiri.
    if changed_by and changed_by.pk == getattr(ticket.created_by, "pk", None):
        return

    _send(
        subject=ticket_email_subject(ticket),
        message=(
            f"Status tiket kamu berubah dari '{old_status}' menjadi "
            f"'{ticket.get_status_display()}'.\n\n"
            f"Lihat detail tiket di dashboard untuk info lebih lanjut."
        ),
        to=[ticket.created_by.email],
        cc=settings.TICKET_NOTIFICATION_CC,
    )


def send_reply_notification(reply):
    """Kirim notifikasi email saat ada balasan public (bukan internal note)."""
    if reply.type != reply.Type.PUBLIC_REPLY:
        return

    ticket = reply.ticket
    # Tentukan penerima: kalau yang balas agent/admin, notif ke customer pembuat
    # tiket; kalau yang balas customer, notif ke inbox support.
    if reply.author and reply.author.is_customer:
        recipients = [settings.EMAIL_HOST_USER] if settings.EMAIL_HOST_USER else []
    else:
        recipients = [ticket.created_by.email] if ticket.created_by and ticket.created_by.email else []

    if not recipients:
        return

    _send(
        subject=ticket_email_subject(ticket),
        message=reply.message,
        to=recipients,
        cc=settings.TICKET_NOTIFICATION_CC,
    )